"""News/search tool — recent headlines via DuckDuckGo (no API key)."""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, register


def _news(query: str, max_results: int = 5) -> dict[str, Any]:
    """Return recent news headlines and snippets for a company or topic."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"News lookup failed: {exc}"}

    items = [
        {
            "title": r.get("title"),
            "source": r.get("source"),
            "date": r.get("date"),
            "snippet": (r.get("body") or "")[:280],
            "url": r.get("url"),
        }
        for r in results
    ]
    return {"query": query, "count": len(items), "articles": items}


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
