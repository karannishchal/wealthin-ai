"""Canned response used when no LLM key is configured, so the demo never 404s."""
from __future__ import annotations

_EXAMPLE = (
    "**Demo mode** — no LLM key is configured, so here is a pre-recorded example "
    "of what WealthIn.AI produces.\n\n"
    "**Q: Compare Apple and Microsoft over the last 3 months and flag risks for a "
    "cautious investor.**\n\n"
    "I called `get_market_data` for AAPL and MSFT, then `search_news` for recent "
    "headlines.\n\n"
    "- **Apple (AAPL):** +6.2% over 3 months; P/E ~31; concentration in iPhone revenue "
    "remains a cyclical risk.\n"
    "- **Microsoft (MSFT):** +9.8% over 3 months; P/E ~35; growth tied to Azure/AI "
    "capex, which lifts valuation sensitivity to rate expectations.\n\n"
    "**For a cautious investor:** both are large, profitable and liquid, but trade at "
    "premium multiples — meaning more downside if AI/growth expectations cool. "
    "Diversification across sectors would reduce single-name and theme concentration."
)


def demo_answer(_message: str) -> dict:
    return {
        "answer": _EXAMPLE,
        "trace": [
            {"kind": "llm", "provider": "demo", "decided": "call_tools",
             "tools": ["get_market_data", "search_news"]},
            {"kind": "tool", "name": "get_market_data"},
            {"kind": "tool", "name": "search_news"},
            {"kind": "llm", "provider": "demo", "decided": "final_answer"},
        ],
        "demo_mode": True,
    }
