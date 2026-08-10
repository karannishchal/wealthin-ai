"""Market-data tool — prices and fundamentals via yfinance (no API key).

Uses `history()` for price action and `fast_info` for cheap fundamentals.
`fast_info` avoids yfinance's slow `.info` web-scrape, which can hang for
tens of seconds per ticker — keeping responses fast and reliable.
"""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, register


def _market_data(ticker: str, period: str = "3mo") -> dict[str, Any]:
    """Return recent price action and key stats for a ticker (fast)."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    if hist.empty:
        return {"error": f"No data found for ticker '{ticker}'. Check the symbol."}

    close = hist["Close"]
    start_price = float(close.iloc[0])
    last_price = float(close.iloc[-1])
    pct_change = (last_price - start_price) / start_price * 100 if start_price else 0.0

    out: dict[str, Any] = {
        "ticker": ticker.upper(),
        "period": period,
        "last_price": round(last_price, 2),
        "period_start_price": round(start_price, 2),
        "period_change_pct": round(pct_change, 2),
        "period_high": round(float(close.max()), 2),
        "period_low": round(float(close.min()), 2),
    }

    # fast_info is a lightweight, cached accessor — no slow scrape.
    try:
        fi = t.fast_info
        out["market_cap"] = getattr(fi, "market_cap", None)
        out["currency"] = getattr(fi, "currency", None)
        out["year_high"] = getattr(fi, "year_high", None)
        out["year_low"] = getattr(fi, "year_low", None)
    except Exception:  # noqa: BLE001 - fundamentals are best-effort
        pass

    return out


register(
    Tool(
        name="get_market_data",
        description=(
            "Fetch recent price performance and key stats (price, % change over the "
            "period, 52-week high/low, market cap) for a single stock or ETF ticker."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol, e.g. AAPL, MSFT, VOO."},
                "period": {
                    "type": "string",
                    "description": "History window.",
                    "enum": ["1mo", "3mo", "6mo", "1y", "2y"],
                    "default": "3mo",
                },
            },
            "required": ["ticker"],
        },
        func=_market_data,
    )
)
