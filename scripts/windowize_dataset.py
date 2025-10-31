import pandas as pd, os, re

SRC = "data/processed/dataset.csv"
DST = "data/processed/dataset_windowed.csv"

def windows(text, size=350, step=250, minlen=120):
    text = re.sub(r"\s+", " ", str(text)).strip()
    out = []
    for i in range(0, max(1, len(text)-size+1), step):
        chunk = text[i:i+size]
        if len(chunk) >= minlen:
            out.append(chunk)
    if not out and len(text) >= minlen:
        out = [text[:size]]
    return out

df = pd.read_csv(SRC)
rows = []
for _, r in df.iterrows():
    for w in windows(r["text"]):
        rows.append({**r, "text": w})
df2 = pd.DataFrame(rows).drop_duplicates(subset=["text","archetype"])
os.makedirs("data/processed", exist_ok=True)
df2.to_csv(DST, index=False)
print("Saved", DST, "rows:", len(df2))