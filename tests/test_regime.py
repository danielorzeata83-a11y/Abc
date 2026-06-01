"""Tests for the market-trend regime gate (no look-ahead)."""

import numpy as np
import pytest

from markov.regime import market_index, market_trend_gate


def _panel_trend_then_crash(T=300, N=5):
    up = np.full((150, N), 0.01)
    down = np.full((150, N), -0.01)
    rets = np.vstack([up, down])
    return 100 * np.cumprod(1 + rets, axis=0)


def test_market_index_equal_weight_monotone_in_uptrend():
    prices = 100 * np.cumprod(1 + np.full((50, 4), 0.01), axis=0)
    idx = market_index(prices)
    assert len(idx) == 50
    assert idx[-1] > idx[0]


def test_gate_on_in_uptrend_off_in_downtrend():
    prices = _panel_trend_then_crash()
    gate = market_trend_gate(prices, window=50)
    # Deep in the uptrend -> risk-on; deep in the crash -> risk-off.
    assert gate[140] == 1.0
    assert gate[290] == 0.0


def test_gate_flat_during_warmup():
    prices = _panel_trend_then_crash()
    gate = market_trend_gate(prices, window=50)
    assert np.all(gate[:50] == 0.0)


def test_gate_uses_past_only_length_matches():
    prices = _panel_trend_then_crash()
    gate = market_trend_gate(prices, window=50)
    assert len(gate) == prices.shape[0]
    assert set(np.unique(gate)) <= {0.0, 1.0}
