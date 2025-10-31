import os, glob, json, pandas as pd

RAW = "data/raw"
OUT = "data/processed/dataset.csv"

rows = []
for path in glob.glob(f"{RAW}/*.jsonl"):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
                rows.append({
                    "text": o.get("text",""),
                    "archetype": o.get("archetype",""),
                    "brand": o.get("brand",""),
                    "source": o.get("source",""),
                    "url": o.get("url","")
                })
            except:
                pass

df = pd.DataFrame(rows)
df = df.dropna(subset=["text","archetype"])
df = df[df["text"].str.len() >= 100]
os.makedirs("data/processed", exist_ok=True)
df.to_csv(OUT, index=False)
print(f"✅ Saved {OUT} with {len(df)} rows")