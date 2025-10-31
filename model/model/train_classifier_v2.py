import os, re, random, numpy as np, pandas as pd
from collections import defaultdict
from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import classification_report, confusion_matrix
from model.lexicon import ARCHETYPES

random.seed(42)
np.random.seed(42)

DATA_IN  = "data/processed/dataset.csv"
MODEL_OUT = "model/model_v2.joblib"

# ---------- utilities ----------
def normalize_text(s: str) -> str:
    s = re.sub(r"http\\S+"," ", s)
    s = re.sub(r"[^A-Za-z0-9\\s\\-’'’]", " ", s)
    s = re.sub(r"\\s+"," ", s).strip().lower()
    return s

def clip_text(s: str, max_chars: int = 1400) -> str:
    # keep the first chunk; it usually has headline/mission/tone
    s = s[:max_chars]
    return s

class LexiconFeaturizer(BaseEstimator, TransformerMixin):
    """keyword hit count + coverage per archetype (0..1)"""
    def __init__(self, arch=ARCHETYPES):
        self.arch = arch

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = []
        for t in X:
            t = str(t).lower()
            feats = []
            for _, lex in self.arch.items():
                kws = [k.lower() for k in lex.get("keywords", [])]
                hits = 0
                for w in kws:
                    # allow hyphen variant for well-being
                    w2 = w.replace("well-being","well[- ]being")
                    if re.search(rf"(?:^|[^a-z0-9]){w2}(?:[^a-z0-9]|$)", t):
                        hits += 1
                feats += [hits, hits / max(1, len(kws))]
            rows.append(feats)
        return np.array(rows, dtype=float)

def stratified_group_split(df, label_col="archetype", group_col="brand", test_ratio=0.25):
    """
    Ensure each label appears in the test set by sampling groups (brands) per label.
    Returns train_idx, test_idx (index arrays into df)
    """
    labels = df[label_col].unique().tolist()
    test_groups = set()
    for lab in labels:
        sub = df[df[label_col]==lab]
        groups = sub[group_col].dropna().unique().tolist()
        if not groups:  # fallback
            continue
        k = max(1, round(len(groups) * test_ratio))
        # sample groups for this label
        random.shuffle(groups)
        chosen = set(groups[:k])
        test_groups |= chosen
    is_test = df[group_col].isin(test_groups)
    # Edge case: if any label still missing in test (e.g., all examples share a group),
    # move one brand for that label to test.
    for lab in labels:
        if (df[is_test & (df[label_col]==lab)].empty):
            sub = df[df[label_col]==lab]
            g = sub[group_col].iloc[0]
            is_test |= (df[group_col]==g)
    test_idx = df[is_test].index.values
    train_idx = df[~is_test].index.values
    return train_idx, test_idx

# ---------- load & clean ----------
df = pd.read_csv(DATA_IN)
df = df.dropna(subset=["text","archetype"])
df["text"] = df["text"].astype(str).map(normalize_text).map(clip_text)
df["brand"] = df.get("brand", pd.Series(["unknown"]*len(df)))

# drop duplicates on normalized text
df = df.drop_duplicates(subset=["text","archetype"])

# show class balance pre-split
print("Dataset size:", len(df))
print("Counts per class:\n", df["archetype"].value_counts())

# ---------- stratified group split by brand ----------
train_idx, test_idx = stratified_group_split(df, "archetype", "brand", test_ratio=0.25)
tr, te = df.loc[train_idx], df.loc[test_idx]
print("\nBrands in test:", sorted(te["brand"].unique().tolist()))
print("Test counts per class:\n", te["archetype"].value_counts())

# ---------- features ----------
word = TfidfVectorizer(ngram_range=(1,2), min_df=2, sublinear_tf=True, max_features=120000)
char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), min_df=2, max_features=120000)
lex  = LexiconFeaturizer()

features = FeatureUnion([
    ("word", word),
    ("char", char),
    ("lex",  lex)
])

# ---------- classifier (SVM + calibrated probs) ----------
base = LinearSVC(C=2.0, class_weight="balanced")
clf  = CalibratedClassifierCV(base, method="isotonic", cv=3)

pipe = Pipeline([("features", features), ("clf", clf)])
pipe.fit(tr["text"], tr["archetype"])

pred  = pipe.predict(te["text"])
probs = pipe.predict_proba(te["text"])
print("\nClassification Report:")
print(classification_report(te["archetype"], pred, digits=3))
print("Confusion matrix:\n", confusion_matrix(te["archetype"], pred))

dump(pipe, MODEL_OUT)
print(f"✅ Model saved to {MODEL_OUT}")