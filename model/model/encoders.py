import re, numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sentence_transformers import SentenceTransformer
from .lexicon import ARCHETYPES

def _norm(s: str) -> str:
    s = re.sub(r"http\\S+"," ", s)
    s = re.sub(r"[^A-Za-z0-9\\s\\-’'’]", " ", s)
    s = re.sub(r"\\s+"," ", s).strip().lower()
    return s

class SBERTEncoder(BaseEstimator, TransformerMixin):
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", max_chars=1400):
        self.model_name = model_name; self.max_chars = max_chars; self._m = None
    def fit(self, X, y=None):
        if self._m is None: self._m = SentenceTransformer(self.model_name)
        return self
    def transform(self, X):
        if self._m is None: self._m = SentenceTransformer(self.model_name)
        texts = [_norm(str(t))[:self.max_chars] for t in X]
        emb = self._m.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(emb, dtype=np.float32)

class LexiconFeaturizer(BaseEstimator, TransformerMixin):
    def __init__(self, arch=ARCHETYPES): self.arch = arch
    def fit(self, X, y=None): return self
    def transform(self, X):
        rows = []
        for t in X:
            t = str(t).lower(); feats = []
            for _, lex in self.arch.items():
                kws = [k.lower() for k in lex.get("keywords", [])]
                hits = 0
                for w in kws:
                    w2 = w.replace("well-being","well[- ]being")
                    if re.search(rf"(?:^|[^a-z0-9]){w2}(?:[^a-z0-9]|$)", t): hits += 1
                feats += [hits, hits/max(1,len(kws))]
            rows.append(feats)
        return np.array(rows, dtype=float)