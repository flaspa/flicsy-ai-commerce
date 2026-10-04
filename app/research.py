"""Real evidence adapters: Andy -> Tavily, Emily -> Bright Data clipping book, Serena -> Moss.

Each returns {"status": "LIVE"|"CLIPBOOK"|"FALLBACK", ...}. On any failure the caller gets status FALLBACK and
an error string, and the workflow continues. Nothing here invents sources, clips or products.
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import re
import time

import httpx

from app.config import PROJECT_ROOT

# ------------------------------- Andy: Tavily -------------------------------
FASHION_DOMAINS = ["vogue.com", "harpersbazaar.com", "elle.com", "wwd.com", "thecut.com", "businessoffashion.com",
                   "whowhatwear.com", "gq.com", "dazeddigital.com", "nytimes.com"]


async def tavily_search(query: str, max_results: int = 4) -> dict:
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as h:
            r = await h.post("https://api.tavily.com/search",
                             headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
                             json={"query": query, "max_results": max_results, "search_depth": "basic",
                                   "include_domains": FASHION_DOMAINS})
        r.raise_for_status()
        titles: set[str] = set()
        sources = [{"title": x["title"], "url": x["url"], "publication": _pub(x["url"]), "snippet": (x.get("content") or "")[:280]}
                   for x in r.json().get("results", []) if not (x["title"] in titles or titles.add(x["title"]))][:max_results]
        if not sources:
            raise RuntimeError("no results")
        return {"status": "LIVE", "query": query, "sources": sources, "ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as exc:
        print(f"[tavily] FALLBACK: {exc!r}")
        return {"status": "FALLBACK", "query": query, "sources": [], "error": str(exc)[:200]}


def _pub(url: str) -> str:
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return {"vogue.com": "Vogue", "harpersbazaar.com": "Harper's Bazaar", "elle.com": "ELLE", "wwd.com": "WWD",
            "thecut.com": "The Cut", "businessoffashion.com": "Business of Fashion", "whowhatwear.com": "Who What Wear",
            "gq.com": "GQ", "dazeddigital.com": "Dazed", "nytimes.com": "The New York Times"}.get(host, host)


# ------------------------------- Emily: Bright Data clipping book -------------------------------
# Real TikTok posts collected by Mira Picks through the Bright Data "TikTok - Posts by Search URL" dataset.
CLIP_DIR = PROJECT_ROOT / "data" / "brightdata"
_CLIPS: list[dict] | None = None
STOP = set("the and for with this that your are not but from have what when just like get can all out one our its "
           "into about than then there here over under outfit outfits fashion style look looks wear wearing".split())


def _clips() -> list[dict]:
    global _CLIPS
    if _CLIPS is None:
        seen: dict[str, dict] = {}
        for line in (CLIP_DIR / "tiktok_clipbook.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                seen[c.get("post_id") or c["url"]] = c
        for f in glob.glob(str(CLIP_DIR / "demo" / "*.json")):
            for c in json.loads(open(f, encoding="utf-8").read())["clips"]:
                seen.setdefault(c.get("post_id") or c["url"], c)
        _CLIPS = list(seen.values())
    return _CLIPS


# Fashion concepts Emily can look for: group -> (trend label shown on the card, [(phrase, weight)], [hashtags]).
CONCEPTS = {
    "evening": ("Dressing up for evening events",
                [("black tie", 4), ("gala", 4), ("red carpet", 4), ("evening", 3), ("gown", 3), ("couture", 3),
                 ("oscar party", 4), ("dressing up", 3), ("satin", 2), ("events", 2), ("party", 1)],
                ["redcarpet", "couture", "hautecouture", "eveningwear", "gala", "blacktie", "oscars", "elegantstyle"]),
    "tailoring": ("Tailoring as eveningwear",
                  [("sculptural tailoring", 5), ("tailoring", 3), ("tailored", 3), ("skirt suit", 4), ("suit", 2),
                   ("tuxedo", 4), ("blazer", 3), ("fitted silhouettes", 3)],
                  ["tailoring", "suiting", "tuxedo", "blazer"]),
    "blue": ("Blue as an evening colour",
             [("cobalt", 4), ("royal blue", 4), ("midnight blue", 4), ("navy", 2), ("blue", 2)],
             ["cobalt", "royalblue", "blueoutfit"]),
    "low_heels": ("Comfortable low heels and flats",
                  [("kitten heel", 4), ("micro heel", 4), ("ballet flat", 4), ("comfy heels", 4), ("comfortable", 2),
                   ("heels all night", 4), ("easy to walk in", 3), ("flats", 2)],
                  ["kittenheels", "balletflats", "comfyheels", "flatshoes"]),
}


def fashion_terms(brief: dict) -> dict[str, tuple]:
    """Fashion concepts implied by the brief's fields — never generic words from the conversation."""
    text = " ".join(str(v) for v in brief.values() if isinstance(v, str)).lower()
    groups = {}
    if re.search(r"gala|black tie|formal|cocktail|wedding|evening|party", text):
        groups["evening"] = CONCEPTS["evening"]
    if re.search(r"suit|either|tailor|unconventional", text):
        groups["tailoring"] = CONCEPTS["tailoring"]
    if "blue" in text:
        groups["blue"] = CONCEPTS["blue"]
    if re.search(r"stiletto|flat|low heel|comfort", text):
        groups["low_heels"] = CONCEPTS["low_heels"]
    return groups or {"evening": CONCEPTS["evening"]}


def _score_clip(c: dict, groups: dict) -> tuple[float, dict[str, list[str]]]:
    cap = (c.get("description") or "").lower()
    tags = {t.lower() for t in (c.get("hashtags") or [])}
    hits: dict[str, list[str]] = {}
    score = 0.0
    for g, (_, phrases, hashtags) in groups.items():
        for phrase, w in phrases:
            if re.search(r"\b" + re.escape(phrase), cap):
                score += w
                hits.setdefault(g, []).append(phrase)
        for h in hashtags:
            if h in tags:
                score += 3
                hits.setdefault(g, []).append("#" + h)
    if hits and (c.get("create_time") or "").startswith("2026"):
        score += 0.5  # recency, only once a clip is relevant
    return score, hits


def clipbook_query(brief: dict, limit: int = 4, threshold: float = 4.0, per_group: int = 2) -> dict:
    """Rank the real clipping book by fashion relevance first; engagement only breaks ties."""
    t0 = time.perf_counter()
    try:
        clips = _clips()
        groups = fashion_terms(brief)
        scored = []
        for c in clips:
            s, hits = _score_clip(c, groups)
            if s > 0:
                scored.append((s, c.get("play_count") or 0, c, hits))
        scored.sort(key=lambda x: (-x[0], -x[1]))
        picked, rejected, used = [], [], {}
        for s, plays, c, hits in scored:
            main = max(hits, key=lambda g: len(hits[g]))
            reason = ("below relevance threshold" if s < threshold else
                      f"already {per_group} clips for '{groups[main][0]}'" if used.get(main, 0) >= per_group else
                      "limit reached" if len(picked) >= limit else "")
            row = {"text": (c.get("description") or "")[:160], "url": c["url"], "creator": c.get("profile_username"),
                   "plays": plays, "tags": (c.get("hashtags") or [])[:4], "date": (c.get("create_time") or "")[:10],
                   "score": round(s, 1), "matched": [p for v in hits.values() for p in v], "trend": groups[main][0]}
            if reason:
                rejected.append({**row, "reason": reason})
            else:
                used[main] = used.get(main, 0) + 1
                picked.append(row)
        return {"status": "CLIPBOOK", "searched": len(clips), "matched": len(picked),
                "terms": [p for _, ps, _ in groups.values() for p, _ in ps][:16],
                "concepts": [label for label, _, _ in groups.values()], "clips": picked, "rejected": rejected[:8],
                "ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as exc:
        print(f"[clipbook] FALLBACK: {exc!r}")
        return {"status": "FALLBACK", "searched": 0, "matched": 0, "clips": [], "error": str(exc)[:200]}


# ------------------------------- Serena: complements (Moss index covers dresses only) -------------------------------
# Real in-stock Everlane products from the public catalog feed (snapshot 2026-10-03): shoes, outerwear, tailoring, bags.
_COMPLEMENTS: list[dict] | None = None
SLOTS = {"shoes": ("Flats + Other", "Boots", "Footwear"), "outer": ("Outerwear",),
         "tailoring": ("Bottoms", "Shirting", "Woven Tops"), "accessory": ("Bags", "Accessories")}


def complements(query: str, per_slot: int = 3) -> list[dict]:
    global _COMPLEMENTS
    if _COMPLEMENTS is None:
        _COMPLEMENTS = json.loads((PROJECT_ROOT / "data" / "catalog" / "everlane_complements.json").read_text(encoding="utf-8"))
    words = {w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in STOP}
    score = lambda p: sum(w in (p["name"] + " " + p["color"] + " " + p["type"]).lower() for w in words)
    out = []
    for slot, types in SLOTS.items():
        pool = sorted((p for p in _COMPLEMENTS if p["type"] in types), key=lambda p: -score(p))
        out += [{**p, "slot": slot, "source": "Everlane catalog"} for p in pool[:per_slot]]
    return out


# ------------------------------- Serena: Moss -------------------------------
MOSS_INDEX = "everlane-com"
_MOSS = None
_MOSS_LOCK = asyncio.Lock()
# Collection-page chunks: [![Name](image)](product-url) ... [Name](product-url) $price [$was]
PROD = re.compile(r"\[!\[([^\]]+)\]\((https://cdn\.shopify\.com[^)\s]+)\)\]\((https://www\.everlane\.com/products/[^)\s]+)\)")
PRICE = re.compile(r"\$(\d+(?:\.\d\d)?)")


async def moss_client():
    global _MOSS
    async with _MOSS_LOCK:
        if _MOSS is None:
            from moss import MossClient
            client = MossClient(os.environ["MOSS_PROJECT_ID"], os.environ["MOSS_PROJECT_KEY"])
            await client.load_index(MOSS_INDEX)  # ~10 s once; queries are then ~1 ms
            _MOSS = client
    return _MOSS


LINK = re.compile(r"(?<!!)\[([^\]!]+)\]\((https://www\.everlane\.com/products/[^)\s]+)\)\s*((?:\$\d+(?:\.\d\d)?\s*){1,2})")


def _products(text: str) -> list[dict]:
    """Products as rendered on the crawled collection pages: an image link plus a text link followed by price(s)."""
    images = {m.group(3): re.sub(r"_\d+x\.jpg", "_700x.jpg", m.group(2)) for m in PROD.finditer(text)}
    out = []
    for m in LINK.finditer(text):
        url = m.group(2)
        if url not in images:
            continue
        prices = [float(p) for p in PRICE.findall(m.group(3))[:2]]
        price, was = prices[0], (prices[1] if len(prices) > 1 and prices[1] > prices[0] else None)
        out.append({"name": m.group(1).strip(), "url": url, "img": images[url], "price": price, "was": was, "color": "",
                    "retailer": "Everlane", "stock": "Listed on everlane.com", "source": "Moss · everlane-com"})
    return out


async def moss_search(query: str, top_k: int = 20, limit: int = 8) -> dict:
    t0 = time.perf_counter()
    try:
        from moss import QueryOptions
        client = await moss_client()
        seen: dict[str, dict] = {}
        for q in (query, "evening dress"):  # the index is collection-page chunks; widen once if the first pass is thin
            res = await client.query(MOSS_INDEX, q, QueryOptions(top_k=top_k))
            for d in res.docs:
                for p in _products(d.text):
                    seen.setdefault(p["url"], p)
            if len(seen) >= 4:
                break
        products = list(seen.values())[:limit]
        if not products:
            raise RuntimeError("no products parsed")
        for i, p in enumerate(products):
            p["id"] = f"m{i + 1}"
        return {"status": "LIVE", "query": query, "index": MOSS_INDEX, "products": products, "chunks": len(res.docs),
                "moss_ms": res.time_taken_ms, "ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as exc:
        print(f"[moss] FALLBACK: {exc!r}")
        return {"status": "FALLBACK", "query": query, "products": [], "error": str(exc)[:200]}
