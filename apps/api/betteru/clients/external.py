"""Small clients for optional third-party APIs. Each returns None / [] when
its API key is missing or the call fails, so features degrade gracefully."""

import logging
import re

import httpx

from betteru.config import get_settings

log = logging.getLogger(__name__)

# Web search is limited to sources we trust for health information.
TRUSTED_DOMAINS = [
    "who.int", "nih.gov", "ods.od.nih.gov", "medlineplus.gov", "cdc.gov",
    "dietaryguidelines.gov", "usda.gov", "canada.ca", "food-guide.canada.ca",
    "nhs.uk", "eatright.org", "heart.org", "mayoclinic.org", "hsph.harvard.edu",
    "jissn.biomedcentral.com", "acsm.org",
]

YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_recipe_video(query: str) -> str | None:
    key = get_settings().youtube_api_key
    if not key or not query.strip():
        return None
    try:
        r = httpx.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": key, "q": f"{query} recipe", "part": "snippet", "type": "video",
                "maxResults": 1, "videoEmbeddable": "true", "safeSearch": "strict",
            },
            timeout=8,
        )
        r.raise_for_status()
        items = r.json().get("items") or []
        vid = items[0]["id"]["videoId"] if items else None
        return vid if vid and YT_ID_RE.match(vid) else None
    except Exception as e:  # noqa: BLE001 — optional feature
        log.warning("YouTube search failed: %s", e)
        return None


def web_search(query: str, max_results: int = 4) -> list[dict]:
    """Trusted-domain web search via Tavily. Results are used for one answer
    only — never written into the knowledge base."""
    key = get_settings().tavily_api_key
    if not key:
        return []
    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key, "query": query, "search_depth": "advanced",
                "max_results": max_results, "include_domains": TRUSTED_DOMAINS,
            },
            timeout=15,
        )
        r.raise_for_status()
        return [
            {"title": x.get("title", ""), "url": x.get("url", ""), "content": (x.get("content") or "")[:1200]}
            for x in r.json().get("results", [])
            if x.get("content")
        ]
    except Exception as e:  # noqa: BLE001
        log.warning("Tavily search failed: %s", e)
        return []


def open_food_facts_product(barcode: str) -> dict | None:
    """Look up a packaged food by barcode (free, no key)."""
    if not re.fullmatch(r"\d{6,14}", barcode):
        return None
    try:
        r = httpx.get(
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
            params={"fields": "product_name,brands,categories,nutriments,serving_size,serving_quantity"},
            headers={"User-Agent": "BetterU/1.0 (nutrition app)"},
            timeout=10,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        return data.get("product") if data.get("status") == 1 else None
    except Exception as e:  # noqa: BLE001
        log.warning("Open Food Facts lookup failed: %s", e)
        return None
