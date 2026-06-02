"""Tests for the value+quality screener (separates value from value traps)."""

import numpy as np
import pandas as pd
import pytest
from markov.screener import compute_scores, QUADRANTS


def _df():
    # 4 Tech stocks: cheap+quality, cheap+junk(trap), pricey+quality, pricey+junk
    return pd.DataFrame({
        "Symbol": ["CHEAPQ", "TRAP", "PRICEYQ", "JUNK"],
        "Sector": ["Tech"] * 4,
        "Price/Earnings": [8.0, 9.0, 40.0, 38.0],
        "Price/Book": [1.0, 1.1, 5.0, 4.8],
        "Price/Sales": [1.0, 1.1, 5.0, 4.8],
        "Market Cap": [1e9] * 4,
        "EBITDA": [4e8, 2e7, 4e8, 2e7],   # margin high for Q names, low for junk
        "Dividend Yield": [0.03, 0.0, 0.01, 0.0],
    })


def test_scores_columns_present():
    out = compute_scores(_df())
    for c in ["value_pct", "quality_pct", "quadrant", "EBITDA Margin"]:
        assert c in out.columns


def test_cheap_quality_identified():
    out = compute_scores(_df()).set_index("Symbol")
    assert out.loc["CHEAPQ", "value_pct"] >= 50
    assert out.loc["CHEAPQ", "quality_pct"] >= 50
    assert out.loc["CHEAPQ", "quadrant"] == "CHEAP + QUALITY"


def test_value_trap_flagged():
    out = compute_scores(_df()).set_index("Symbol")
    # TRAP is cheap but low margin -> trap risk
    assert out.loc["TRAP", "value_pct"] >= 50
    assert out.loc["TRAP", "quality_pct"] < 50
    assert "TRAP" in out.loc["TRAP", "quadrant"] or "LOW QUALITY" in out.loc["TRAP", "quadrant"]


def test_ebitda_margin_derived():
    out = compute_scores(_df()).set_index("Symbol")
    # Sales = MarketCap / (P/S) = 1e9/1.0 = 1e9; margin = 4e8/1e9 = 0.4
    assert out.loc["CHEAPQ", "EBITDA Margin"] == pytest.approx(0.4, abs=1e-6)


def test_quadrants_constant_has_four():
    assert len(QUADRANTS) == 4


def test_financials_use_roe_when_no_ebitda():
    # Banks have no EBITDA -> quality should fall back to ROE (=PB/PE), not n/a
    df = pd.DataFrame({
        "Symbol": ["BANKA", "BANKB", "BANKC", "BANKD"],
        "Sector": ["Financial Services"] * 4,
        "Price/Earnings": [8.0, 10.0, 12.0, 20.0],
        "Price/Book": [1.6, 1.0, 0.8, 1.0],   # ROE = PB/PE: 0.20,0.10,0.067,0.05
        "Price/Sales": [2.0, 2.0, 2.0, 2.0],
        "Market Cap": [1e9] * 4,
        "EBITDA": [float("nan")] * 4,           # banks: no EBITDA
        "Dividend Yield": [0.03, 0.03, 0.02, 0.01],
    })
    out = compute_scores(df).set_index("Symbol")
    # BANKA has the highest ROE (0.20) -> highest quality among the banks
    assert out.loc["BANKA", "quality_pct"] > out.loc["BANKD", "quality_pct"]
    assert out.loc["BANKA", "quadrant"] != "n/a"
