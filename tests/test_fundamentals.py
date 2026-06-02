"""Tests for per-stock valuation context (relative, honest -- not a signal)."""

import pandas as pd
import pytest
from markov.fundamentals import valuation_context, cheaper_than_pct


def _df():
    return pd.DataFrame({
        "Symbol": ["AAA", "BBB", "CCC", "DDD"],
        "Sector": ["Tech", "Tech", "Tech", "Energy"],
        "Price/Earnings": [10.0, 20.0, 30.0, 15.0],
        "Price/Book": [1.0, 2.0, 3.0, 1.5],
        "Price/Sales": [1.0, 2.0, 3.0, 1.5],
        "Dividend Yield": [0.03, 0.02, 0.01, 0.04],
    })


def test_cheaper_than_pct_lower_is_cheaper():
    # P/E of 10 is cheaper than the two peers at 20 and 30 -> ~67%
    pct = cheaper_than_pct(10.0, [10.0, 20.0, 30.0])
    assert pct == pytest.approx(66.7, abs=1.0)


def test_valuation_context_fields_and_relative():
    ctx = valuation_context(_df(), "AAA")
    assert ctx["ticker"] == "AAA" and ctx["sector"] == "Tech"
    assert ctx["pe"] == 10.0
    # cheapest in its Tech sector -> high cheaper-than within sector
    assert ctx["sector_cheaper_pct"] > 50
    assert ctx["label"] in {"CHEAP vs sector", "NORMAL vs sector", "EXPENSIVE vs sector"}


def test_expensive_stock_labeled():
    ctx = valuation_context(_df(), "CCC")  # highest P/E in Tech
    assert ctx["label"] == "EXPENSIVE vs sector"


def test_unknown_ticker_raises():
    with pytest.raises(KeyError):
        valuation_context(_df(), "ZZZ")
