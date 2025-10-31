import os, json, argparse, time, requests
from youtube_transcript_api import YouTubeTranscriptApi

OUTDIR = "data/raw"

def search_videos(api_key, q, max_results=10):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"key": api_key, "q": q, "part": "snippet", "type": "video", "maxResults": max_results}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return [item["id"]["videoId"] for item in r.json().get("items", [])]

def get_transcript(video_id: str) -> str:
    try:
        lines = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return " ".join([x["text"] for x in lines])
    except Exception:
        return ""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--archetype", required=True, choices=["Rebel","Caregiver","Explorer"])
    ap.add_argument("--query", required=True)
    ap.add_argument("--api_key", required=True)
    ap.add_argument("--max_results", type=int, default=10)
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    out_path = f"{OUTDIR}/{args.brand}_{args.archetype}_youtube.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for vid in search_videos(args.api_key, args.query, args.max_results):
            text = get_transcript(vid)
            if len(text) < 200: continue
            f.write(json.dumps({
                "brand": args.brand, "archetype": args.archetype,
                "source": "youtube_transcript", "url": f"https://www.youtube.com/watch?v={vid}",
                "text": text[:4000]
            }, ensure_ascii=False) + "\n")
            time.sleep(0.2)
    print("✅ Wrote", out_path)