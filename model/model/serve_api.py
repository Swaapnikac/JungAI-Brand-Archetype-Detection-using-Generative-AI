# model/serve_api.py
# FastAPI server for JungAI archetype classifier
#
# - Loads the best available model (v3 -> v2 -> v1)
# - Returns calibrated 0–1 confidence + top-3 scores
# - Robust n-gram keyword matching (unigram/bigram/trigram)
# - Lexicon-aware override when the model is uncertain
#
# Run:
#   source venv311/bin/activate
#   python -m uvicorn model.serve_api:app --reload --port 8008 --host 0.0.0.0

from __future__ import annotations
import os, re, random
from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from joblib import load

from .lexicon import ARCHETYPES

# ---------------------------------------------------------
# App setup
# ---------------------------------------------------------
app = FastAPI(title="JungAI (Local)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefer newest model, fall back gracefully
MODEL_PATHS = [
    "model/model_v3.joblib",
    "model/model_v2.joblib",
    "model/model.joblib",
]
model = None
active_model_path = None
for p in MODEL_PATHS:
    if os.path.exists(p):
        model = load(p)
        active_model_path = p
        break

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def normalize_text(s: str) -> str:
    s = re.sub(r"http\S+", " ", s)
    s = re.sub(r"[^A-Za-z0-9\s\-’'’]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# --- robust keyword matching (handles hyphens, punctuation, multiword) ---
def _norm_for_match(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[-–—_/]", " ", s)          # hyphens & dashes -> space
    s = re.sub(r"[^a-z0-9\s]", " ", s)      # drop other punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _ngram_set(text: str) -> set:
    toks = text.split()
    grams = set(toks)  # unigrams
    grams |= set(" ".join(toks[i:i+2]) for i in range(len(toks)-1))  # bigrams
    grams |= set(" ".join(toks[i:i+3]) for i in range(len(toks)-2))  # trigrams
    return grams

def analyze_patterns_all(text: str) -> Dict[str, List[str]]:
    """
    Return { archetype: [matched_keywords...] } using n-grams (1–3).
    Matches are insensitive to punctuation/hyphen differences and spacing.
    """
    norm_text = _norm_for_match(text)
    grams = _ngram_set(norm_text)
    out: Dict[str, List[str]] = {}
    for name, lex in ARCHETYPES.items():
        hits = []
        for kw in lex.get("keywords", []):
            if _norm_for_match(kw) in grams:
                hits.append(kw.lower())
        out[name] = hits
    return out

def rewrite(text: str, target: str, brand: str = "Your brand") -> str:
    """
    Lightweight rewrite using lexicon templates/replacements.
    Produces a short, archetype-aligned line.
    """
    lex = ARCHETYPES.get(target, {})
    # word swaps
    for k, v in lex.get("replace", {}).items():
        text = text.replace(k, v).replace(k.capitalize(), v.capitalize())

    templates = lex.get("templates", [])
    if not templates:
        t = normalize_text(text)
        return (t[:120] + "...") if len(t) > 120 else t

    def pick(key: str, default: str) -> str:
        arr = lex.get(key, [])
        return random.choice(arr) if arr else default

    t = random.choice(templates)
    return t.format(
        brand=brand,
        verb=pick("verbs", "support"),
        verb2=pick("verbs2", "go"),
        verb3=pick("verbs3", "move"),
        benefit=pick("benefits", "what matters"),
    )

# ---------------------------------------------------------
# API schema
# ---------------------------------------------------------
class Inp(BaseModel):
    text: str

# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "model_loaded": bool(model),
        "model_path": active_model_path,
    }

@app.post("/classify")
def classify(inp: Inp):
    if model is None:
        return {"error": "Model not trained. Place model_v3.joblib (or v2/v1) in model/."}

    raw_text = inp.text or ""
    txt = normalize_text(raw_text)

    # 1) Model probabilities (calibrated if v2/v3)
    labels = list(model.classes_)
    probs  = model.predict_proba([txt])[0]
    scores = {labels[i]: float(probs[i]) for i in range(len(labels))}

    # 2) Lexicon matches across all archetypes (robust n-gram)
    found_all = analyze_patterns_all(txt)

    # 3) Model top
    top  = max(scores, key=scores.get)
    conf = scores[top]

    # 4) Lexicon-aware override (conservative but effective)
    # Choose class with most *actual* matches
    lex_label = max(found_all, key=lambda k: len(found_all[k])) if found_all else None
    lex_hits  = {k: len(v) for k, v in found_all.items()}

    # If another class has ≥2 real hits and either:
    #  • beats model's top by ≥2 hits, OR
    #  • model confidence is middling (< 0.55),
    # then switch to that lexicon class.
    if lex_label and lex_label != top:
        strong = lex_hits[lex_label] >= 2
        margin = lex_hits[lex_label] >= (lex_hits.get(top, 0) + 2)
        lowc   = conf < 0.55
        if strong and (margin or lowc):
            top  = lex_label
            conf = round(0.52 + 0.48 * scores.get(top, 0.0), 4)  # blended 0–1

    # Optional: uncertainty bucket
    # if conf < 0.45:
    #     top = "Uncertain"

    # 5) Found/missing for final label
    found_top = found_all.get(top, [])
    all_kws   = [k.lower() for k in ARCHETYPES.get(top, {}).get("keywords", [])]
    missing   = [w for w in all_kws if w not in found_top][:10]

    # 6) Example rewrite
    ex = rewrite(raw_text, top, brand="Your brand")

    # 7) Top-3 (nice for Slack/UI)
    top3 = dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3])

    return {
        "label": top,
        "confidence": round(float(conf), 4),      # 0–1
        "scores": {k: round(v, 4) for k, v in top3.items()},
        "patterns_found": found_top,
        "patterns_missing": missing,
        "patterns_found_all": found_all,          # useful for debugging
        "suggestions": [
            f"Use words like: {', '.join(missing[:5])}" if missing else "Nice coverage of key words.",
            "Use strong, direct verbs; cut corporate jargon."
        ],
        "example_rewrite": ex,
    }

# Local dev entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("model.serve_api:app", host="0.0.0.0", port=8008, reload=True)