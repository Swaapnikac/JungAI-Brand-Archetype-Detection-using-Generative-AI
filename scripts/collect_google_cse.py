import os, json, time, re, argparse, requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

OUTDIR = "data/raw"
UA = "jungai-collector/1.0 (+https://example.local)"

def log(msg: str):
    print(msg, flush=True)

def safe_get(url: str, timeout: int = 15) -> Optional[requests.Response]:
    """GET with small retry; returns Response or None."""
    for i in range(3):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": UA})
            r.raise_for_status()
            return r
        except Exception:
            time.sleep(0.5 * (i + 1))
    return None

def normalize_text(s: str) -> str:
    s = s.replace("\x00", " ")            # strip nulls
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def extract_main_text(html: str) -> str:
    """
    Try readability first (if available); on failure fall back to plain BS4.
    Always remove boilerplate and normalize whitespace.
    """
    soup = None
    try:
        from readability import Document
        doc = Document(html)
        readable_html = doc.summary()
        soup = BeautifulSoup(readable_html, "html.parser")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Drop boilerplate
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    return normalize_text(text)

def fetch_and_clean(url: str) -> str:
    r = safe_get(url)
    if not r:
        return ""
    # make sure encoding is sane for lxml/readability
    try:
        r.encoding = r.apparent_encoding or r.encoding or "utf-8"
    except Exception:
        r.encoding = "utf-8"
    html = r.text
    text = extract_main_text(html)
    return text

def google_search(q: str, api_key: str, cx: str, start: int = 1) -> Dict[str, Any]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": q, "start": start}
    r = safe_get(url + "?" + requests.compat.urlencode(params))
    if not r:
        return {}
    try:
        return r.json()
    except Exception:
        return {}

def collect_links(queries: List[str], api_key: str, cx: str, per_query: int) -> List[str]:
    links = []
    seen = set()
    for q in queries:
        count = 0
        start = 1
        while count < per_query and start <= 91:  # Google CSE supports start up to ~100
            data = google_search(q, api_key, cx, start=start)
            items = data.get("items", []) if isinstance(data, dict) else []
            if not items:
                break
            for it in items:
                link = it.get("link")
                if not link or link in seen:
                    continue
                seen.add(link)
                links.append(link)
                count += 1
                if count >= per_query:
                    break
            # next page
            start += 10
            time.sleep(0.25)  # be nice to the API
    return links

def write_jsonl(path: str, rows: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"✅ Wrote {path} ({len(rows)} rows)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--archetype", required=True, choices=["Rebel", "Caregiver", "Explorer"])
    ap.add_argument("--queries", nargs="+", required=True, help="One or more Google queries")
    ap.add_argument("--api_key", required=True)
    ap.add_argument("--cx", required=True, help="Programmable Search Engine ID")
    ap.add_argument("--per_query", type=int, default=10, help="Max links to fetch per query (default 10)")
    args = ap.parse_args()

    out_path = os.path.join(OUTDIR, f"{args.brand}_{args.archetype}_google.jsonl")

    log(f"🔎 Collecting with queries: {args.queries}")
    links = collect_links(args.queries, args.api_key, args.cx, args.per_query)
    log(f"🔗 Found {len(links)} candidate links")

    rows = []
    kept = 0
    for i, url in enumerate(links, 1):
        txt = fetch_and_clean(url)
        if len(txt) >= 400:  # keep only substantial pages
            rows.append({
                "brand": args.brand,
                "archetype": args.archetype,
                "source": "google_cse",
                "url": url,
                "text": txt[:4000]  # cap text size
            })
            kept += 1
        # light throttle
        time.sleep(0.2)
        if i % 5 == 0:
            log(f"…processed {i}/{len(links)} (kept {kept})")

    if not rows:
        log("⚠️ No usable pages extracted. Try different queries or increase --per_query.")
    write_jsonl(out_path, rows)

if __name__ == "__main__":
    main()