#!/usr/bin/env python3
"""Fetch raw signals for the daily emerging-tech briefing.

Sources:
  * Hacker News (Algolia API): top stories of the last 24h, Show HN, Launch HN (7d)
  * Y Combinator Launches (www.ycombinator.com/launches JSON feed): last ~4 days

Usage:  python3 fetch_sources.py OUT.json
Writes a single JSON file the briefing writer reads. Standard library only.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": "daily-tech-briefing/1.0", "Accept": "application/json"}
NOW = int(time.time())


def get_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # network hiccup: back off and retry
            if i == tries - 1:
                print(f"WARN: {url} failed: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))


def hn_search(tags, since_s, min_points=0, n=50, by_date=False):
    endpoint = "search_by_date" if by_date else "search"
    params = {
        "tags": tags,
        "numericFilters": f"created_at_i>{NOW - since_s},points>{min_points}",
        "hitsPerPage": n,
    }
    url = f"https://hn.algolia.com/api/v1/{endpoint}?" + urllib.parse.urlencode(params)
    d = get_json(url) or {"hits": []}
    out = []
    for h in d["hits"]:
        out.append({
            "title": h.get("title"),
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
            "hn_url": f"https://news.ycombinator.com/item?id={h['objectID']}",
            "points": h.get("points") or 0,
            "comments": h.get("num_comments") or 0,
            "created_at": h.get("created_at"),
            "id": h["objectID"],
        })
    out.sort(key=lambda x: x["points"], reverse=True)
    return out


def hn_top_comments(story_id, k=3):
    """A few top-level comment snippets, to gauge what HN thinks."""
    d = get_json(f"https://hn.algolia.com/api/v1/items/{story_id}")
    if not d:
        return []
    kids = [c for c in d.get("children", []) if c.get("text")]
    snippets = []
    for c in kids[:k]:
        txt = c["text"]
        for tag in ("<p>", "</p>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>"):
            txt = txt.replace(tag, " ")
        txt = urllib.parse.unquote(txt)
        import html as _h, re as _re
        txt = _re.sub(r"<[^>]+>", "", _h.unescape(txt))
        snippets.append(" ".join(txt.split())[:280])
    return snippets


def yc_launches(days=4, max_pages=6):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    seen, out = set(), []
    for page in range(max_pages):
        d = get_json(f"https://www.ycombinator.com/launches?page={page}")
        if not d or not d.get("hits"):
            break
        oldest = None
        for h in d["hits"]:
            if h["id"] in seen:
                continue
            seen.add(h["id"])
            ts = datetime.fromisoformat(h["created_at"].replace("Z", "+00:00"))
            oldest = ts if oldest is None or ts < oldest else oldest
            if ts < cutoff:
                continue
            c = h.get("company") or {}
            out.append({
                "title": h.get("title"),
                "tagline": h.get("tagline"),
                "votes": h.get("total_vote_count", 0),
                "created_at": h["created_at"],
                "company": c.get("name"),
                "company_url": c.get("url"),
                "batch": c.get("batch"),
                "industry": c.get("industry"),
                "tags": c.get("tags") or [],
                "launch_url": h.get("search_path") or f"https://www.ycombinator.com/launches/{h.get('slug')}",
            })
        if oldest and oldest < cutoff:
            break
    out.sort(key=lambda x: x["votes"], reverse=True)
    return out


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "sources.json"
    top = hn_search("story", 86400, min_points=40, n=60)
    show = hn_search("show_hn", 86400 * 2, min_points=10, n=25)
    launch = hn_search("launch_hn", 86400 * 7, min_points=0, n=20, by_date=True)
    for s in top[:12]:
        s["top_comments"] = hn_top_comments(s["id"])
    yc = yc_launches()
    tag_counts = Counter(t for l in yc for t in l["tags"])
    data = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hn_top_24h": top,
        "hn_show_48h": show,
        "hn_launch_7d": launch,
        "yc_launches_4d": yc,
        "yc_tag_counts": tag_counts.most_common(25),
    }
    with open(out_path, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print(f"wrote {out_path}: {len(top)} HN top, {len(show)} Show HN, "
          f"{len(launch)} Launch HN, {len(yc)} YC launches")
    if not top and not yc:
        sys.exit("ERROR: no data fetched from either source")


if __name__ == "__main__":
    main()
