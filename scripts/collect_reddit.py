import os, json, argparse, requests, re

OUTDIR = "data/raw"

def search_reddit(q, limit=60):
    headers = {"User-Agent": "jungai-collector/0.1"}
    url = "https://www.reddit.com/search.json"
    params = {"q": q, "limit": limit, "sort": "relevance", "t": "all"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    if r.status_code != 200:
        return []
    data = r.json().get("data", {}).get("children", [])
    out = []
    for ch in data:
        d = ch.get("data", {})
        text = f"{d.get('title','')} {d.get('selftext','')}"
        text = re.sub(r"\s+", " ", text).strip()
        url = "https://www.reddit.com" + d.get("permalink","") if d.get("permalink") else ""
        if len(text) >= 100:
            out.append({"text": text, "url": url})
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--archetype", required=True, choices=["Rebel","Caregiver","Explorer"])
    ap.add_argument("--query", required=True)
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    out_path = f"{OUTDIR}/{args.brand}_{args.archetype}_reddit.jsonl"
    posts = search_reddit(args.query)
    with open(out_path, "w", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps({
                "brand": args.brand, "archetype": args.archetype,
                "source": "reddit", "url": p["url"], "text": p["text"][:4000]
            }, ensure_ascii=False) + "\n")
    print("✅ Wrote", out_path)