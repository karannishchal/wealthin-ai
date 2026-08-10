"""Portfolio-analysis tool — allocation, concentration and simple risk stats.

Pure, instant maths (no network calls) so it never slows a response.
"""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, register


def _analyse_portfolio(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    """Given holdings [{ticker, value}], compute allocation and concentration."""
    if not holdings:
        return {"error": "No holdings provided."}

    total = sum(float(h.get("value", 0)) for h in holdings)
    if total <= 0:
        return {"error": "Total portfolio value must be positive."}

    rows = []
    for h in holdings:
        ticker = str(h.get("ticker", "")).upper()
        value = float(h.get("value", 0))
        weight = value / total * 100
        rows.append({"ticker": ticker, "value": round(value, 2), "weight_pct": round(weight, 2)})

    rows.sort(key=lambda r: r["weight_pct"], reverse=True)
    # Herfindahl-Hirschman Index (0-1): higher = more concentrated.
    hhi = sum((r["weight_pct"] / 100) ** 2 for r in rows)
    top = rows[0]

    return {
        "total_value": round(total, 2),
        "num_holdings": len(rows),
        "allocations": rows,
        "concentration_hhi": round(hhi, 3),
        "largest_position": {"ticker": top["ticker"], "weight_pct": top["weight_pct"]},
        "notes": (
            "HHI above ~0.25 suggests high concentration; a single position above "
            "20-25% is a common diversification flag."
        ),
    }


register(
    Tool(
        name="analyse_portfolio",
        description=(
            "Analyse a list of portfolio holdings: compute per-position weights and a "
            "concentration score (HHI) to flag diversification risk."
        ),
        parameters={
            "type": "object",
            "properties": {
                "holdings": {
                    "type": "array",
                    "description": "List of holdings.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "value": {"type": "number", "description": "Position value in currency."},
                        },
                        "required": ["ticker", "value"],
                    },
                }
            },
            "required": ["holdings"],
        },
        func=_analyse_portfolio,
    )
)
