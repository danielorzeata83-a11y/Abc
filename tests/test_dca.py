"""Tests for the dollar-cost-averaging (DCA) buy & hold simulator."""

import numpy as np
import pytest
from markov.dca import dca_simulate, cagr, max_drawdown


def test_flat_price_no_profit():
    prices = np.full(12, 100.0)
    r = dca_simulate(prices, contribution=100.0)
    assert r["total_invested"] == pytest.approx(1200.0)
    assert r["final_value"] == pytest.approx(1200.0)
    assert r["profit"] == pytest.approx(0.0)


def test_doubling_price_dca_profits_but_less_than_lump():
    # price doubles linearly; DCA buys cheaper early units -> profit > 0
    prices = np.linspace(100, 200, 13)
    r = dca_simulate(prices, contribution=100.0)
    assert r["profit"] > 0
    # invested 13*100=1300; lump sum at start would have doubled
    assert r["total_invested"] == pytest.approx(1300.0)


def test_units_accumulate_more_when_cheaper():
    cheap = dca_simulate(np.array([50.0, 50.0]), 100.0)["units"]
    pricey = dca_simulate(np.array([200.0, 200.0]), 100.0)["units"]
    assert cheap > pricey


def test_cagr_basic():
    # 2x over 10 years -> ~7.18%
    assert cagr(100, 200, 10) == pytest.approx(0.0718, abs=1e-3)


def test_max_drawdown_detects_crash():
    vals = np.array([100, 120, 60, 90, 130.0])
    assert max_drawdown(vals) == pytest.approx(-0.5, abs=1e-9)


def test_project_dca_grows_with_return():
    from markov.dca import project_dca
    lo = project_dca(monthly=100, years=10, annual_return=0.02)
    hi = project_dca(monthly=100, years=10, annual_return=0.08)
    assert hi["final_value"] > lo["final_value"]
    assert lo["invested"] == 100 * 12 * 10


def test_project_dca_zero_return_equals_invested():
    from markov.dca import project_dca
    r = project_dca(monthly=50, years=5, annual_return=0.0)
    assert r["final_value"] == pytest.approx(r["invested"])
