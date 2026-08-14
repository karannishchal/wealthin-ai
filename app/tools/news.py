"""News/search tool — recent headlines.

Primary source is Google News RSS (works reliably from cloud hosts and needs no
API key). Falls back to DuckDuckGo news if the RSS feed is unavailable.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

from app.tools.base import Tool, register

_UA = "Mozilla/5.0 (compatible; WealthInAI/1.0; +https://wealthin-ai.streamlit.app)"


def _google_news(query: str, max_results: int) -> list[dict[str, Any]]:
    import requests

    url = (
        f"https://news.google.com/rss/search?q={quote_plus(query)}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=12)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items: list[dict[str, Any]] = []
    for it in root.findall(".//item")[:max_results]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        date = (it.findtext("pubDate") or "").strip()
        src_el = it.find("source")
        source = (src_el.text if src_el is not None else "") or ""
        snippet = re.sub("<[^>]+>", "", it.findtext("description") or "").strip()[:280]
        items.append({"title": title, "source": source, "date": date, "snippet": snippet, "url": link})
    return items


def _duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.news(query, max_results=max_results))
    return [
        {
            "title": r.get("title"),
            "source": r.get("source"),
            "date": r.get("date"),
            "snippet": (r.get("body") or "")[:280],
            "url": r.get("url"),
        }
        for r in results
    ]


def _news(query: str, max_results: int = 5) -> dict[str, Any]:
    """Return recent news headlines and snippets for a company or topic."""
    for fetch in (_google_news, _duckduckgo):
        try:
            items = fetch(query, max_results)
            if items:
                return {"query": query, "count": len(items), "articles": items}
        except Exception:  # noqa: BLE001 - try the next source
            continue
    return {"query": query, "count": 0, "articles": [],
            "note": "Live news is temporarily unavailable."}


register(
    Tool(
        name="search_news",
        description=(
            "Search recent news headlines and snippets about a company, sector, or "
            "market topic. Returns titles, sources, dates and URLs for citation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Company, ticker, or topic to search."},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
        func=_news,
    )
)
