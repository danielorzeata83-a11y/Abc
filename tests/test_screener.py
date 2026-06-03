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


def test_no_pe_cannot_be_cheap_quality():
    # A stock with no valid P/E (negative/zero earnings) must NOT surface as a
    # CHEAP+QUALITY candidate even if P/B and P/S look cheap and quality is good.
    # P/E nan = no earnings to be "cheap" against -> value-trap false positive.
    df = pd.DataFrame({
        "Symbol": ["NOPE", "A", "B", "C"],
        "Sector": ["Tech"] * 4,
        "Price/Earnings": [float("nan"), 30.0, 35.0, 40.0],
        "Price/Book": [0.5, 5.0, 5.5, 6.0],     # NOPE looks cheap on P/B
        "Price/Sales": [0.5, 5.0, 5.5, 6.0],    # and on P/S
        "Market Cap": [1e9] * 4,
        # Sales=MktCap/PS; NOPE=2e9, peers=2e8. EBITDA chosen so NOPE has the
        # HIGHEST margin (0.5) -> genuinely high quality, isolating P/E as the
        # only thing that should keep it out of CHEAP+QUALITY.
        "EBITDA": [1e9, 2e7, 2e7, 2e7],
        "Dividend Yield": [0.0] * 4,
    })
    out = compute_scores(df).set_index("Symbol")
    assert out.loc["NOPE", "quality_pct"] >= 50     # genuinely high quality...
    assert out.loc["NOPE", "quadrant"] != "CHEAP + QUALITY"  # ...but no P/E -> blocked


def test_zero_pe_cannot_be_cheap_quality():
    df = pd.DataFrame({
        "Symbol": ["ZERO", "A", "B", "C"],
        "Sector": ["Tech"] * 4,
        "Price/Earnings": [0.0, 30.0, 35.0, 40.0],
        "Price/Book": [0.5, 5.0, 5.5, 6.0],
        "Price/Sales": [0.5, 5.0, 5.5, 6.0],
        "Market Cap": [1e9] * 4,
        "EBITDA": [1e9, 2e7, 2e7, 2e7],
        "Dividend Yield": [0.0] * 4,
    })
    out = compute_scores(df).set_index("Symbol")
    assert out.loc["ZERO", "quadrant"] != "CHEAP + QUALITY"


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
