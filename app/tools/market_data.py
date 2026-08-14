"""Market-data tool — prices and fundamentals via yfinance (no API key).

Uses `history()` for price action and `fast_info` for cheap fundamentals.
`fast_info` avoids yfinance's slow `.info` web-scrape, which can hang for
tens of seconds per ticker — keeping responses fast and reliable.
"""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool, register

_UA = "Mozilla/5.0 (compatible; WealthInAI/1.0)"
_PERIOD_DAYS = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252, "2y": 504}


def _stats(close, ticker: str, period: str, source: str) -> dict[str, Any]:
    start_price = float(close.iloc[0])
    last_price = float(close.iloc[-1])
    pct_change = (last_price - start_price) / start_price * 100 if start_price else 0.0
    return {
        "ticker": ticker.upper(),
        "period": period,
        "last_price": round(last_price, 2),
        "period_start_price": round(start_price, 2),
        "period_change_pct": round(pct_change, 2),
        "period_high": round(float(close.max()), 2),
        "period_low": round(float(close.min()), 2),
        "source": source,
    }


def _from_yfinance(ticker: str, period: str) -> dict[str, Any] | None:
    """Yahoo Finance — great locally, but often blocked from cloud IPs."""
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return None
        out = _stats(hist["Close"], ticker, period, "yfinance")
        try:
            fi = t.fast_info
            out["market_cap"] = getattr(fi, "market_cap", None)
            out["currency"] = getattr(fi, "currency", None)
            out["year_high"] = getattr(fi, "year_high", None)
            out["year_low"] = getattr(fi, "year_low", None)
        except Exception:  # noqa: BLE001 - fundamentals are best-effort
            pass
        return out
    except Exception:  # noqa: BLE001 - fall through to Stooq
        return None


def _from_stooq(ticker: str, period: str) -> dict[str, Any] | None:
    """Stooq CSV — no API key and reliable from cloud hosts (US symbols)."""
    try:
        import io

        import pandas as pd
        import requests

        sym = ticker.lower().replace(".", "-")
        url = f"https://stooq.com/q/d/l/?s={sym}.us&i=d"
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=12)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Close" not in df.columns:
            return None
        df = df.dropna(subset=["Close"])
        win = df.tail(_PERIOD_DAYS.get(period, 66))
        if win.empty:
            return None
        out = _stats(win["Close"], ticker, period, "stooq")
        out["currency"] = "USD"
        return out
    except Exception:  # noqa: BLE001
        return None


def _market_data(ticker: str, period: str = "3mo") -> dict[str, Any]:
    """Return recent price action and key stats for a ticker.

    Tries Yahoo Finance first, then falls back to Stooq (works from the cloud).
    """
    return (
        _from_yfinance(ticker, period)
        or _from_stooq(ticker, period)
        or {"error": f"Live market data for '{ticker}' is temporarily unavailable."}
    )


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
