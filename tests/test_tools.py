"""Unit tests for tools that don't need network/keys."""
from app.tools import schemas
from app.tools.base import get
from app.tools.calculator import _calculate
from app.tools.portfolio import _analyse_portfolio


def test_registry_exposes_all_tools():
    names = {s["function"]["name"] for s in schemas()}
    assert {
        "get_market_data",
        "analyse_portfolio",
        "search_documents",
        "search_news",
        "calculate",
    } <= names


def test_tool_schema_shape():
    tool = get("calculate")
    schema = tool.to_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "calculate"
    assert "properties" in schema["function"]["parameters"]


def test_calculator_valid():
    assert _calculate("(1560-1200)/1200*100")["result"] == 30.0
    assert _calculate("2 ** 10")["result"] == 1024.0


def test_calculator_rejects_code():
    out = _calculate("__import__('os').system('ls')")
    assert "error" in out


def test_portfolio_weights_and_concentration():
    out = _analyse_portfolio(
        [
            {"ticker": "AAPL", "value": 6000},
            {"ticker": "MSFT", "value": 3000},
            {"ticker": "VOO", "value": 1000},
        ]
    )
    assert out["total_value"] == 10000.0
    assert out["allocations"][0]["ticker"] == "AAPL"
    assert out["allocations"][0]["weight_pct"] == 60.0
    assert 0 < out["concentration_hhi"] <= 1


def test_portfolio_empty():
    assert "error" in _analyse_portfolio([])
