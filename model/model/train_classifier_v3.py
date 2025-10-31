import os, re, random, numpy as np, pandas as pd
from joblib import dump
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix
from .encoders import SBERTEncoder, LexiconFeaturizer

random.seed(42); np.random.seed(42)
DATA_IN = "data/processed/dataset_windowed.csv"   # use windowed set
MODEL_OUT = "model/model_v3.joblib"

def norm(s:str)->str:
    s = re.sub(r"http\\S+"," ", s)
    s = re.sub(r"[^A-Za-z0-9\\s\\-’'’]", " ", s)
    s = re.sub(r"\\s+"," ", s).strip().lower()
    return s[:1400]

df = pd.read_csv(DATA_IN)
df = df.dropna(subset=["text","archetype"])
df["text"] = df["text"].astype(str).map(norm)
df["brand"]= df.get("brand", pd.Series(["unknown"]*len(df)))
df = df[df["text"].str.len() >= 120].drop_duplicates(subset=["text","archetype"])

print("Dataset:", len(df))
print("Per class:\\n", df["archetype"].value_counts())

word = TfidfVectorizer(ngram_range=(1,3), min_df=2, sublinear_tf=True, max_features=200000)
char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), min_df=2, max_features=200000)
lex  = LexiconFeaturizer()
sbert= SBERTEncoder()

features = FeatureUnion([("sbert", sbert), ("word", word), ("char", char), ("lex", lex)])
base = LogisticRegression(max_iter=2000, C=6.0, class_weight="balanced", n_jobs=-1)
clf  = CalibratedClassifierCV(base, cv=3, method="isotonic")
pipe = Pipeline([("features", features), ("clf", clf)])

gkf = GroupKFold(n_splits=5)
for fold,(tr,te) in enumerate(gkf.split(df["text"], df["archetype"], df["brand"]),1):
    Xtr, Xte = df.iloc[tr], df.iloc[te]
    pipe.fit(Xtr["text"], Xtr["archetype"])
    p = pipe.predict(Xte["text"])
    print(f"\\nFold {fold} report:")
    print(classification_report(Xte["archetype"], p, digits=3))
    print("Confusion:\\n", confusion_matrix(Xte["archetype"], p))

pipe.fit(df["text"], df["archetype"])
dump(pipe, MODEL_OUT)
print(f"✅ Model saved to {MODEL_OUT}")