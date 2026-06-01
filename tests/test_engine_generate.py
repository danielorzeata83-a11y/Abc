"""Tests for SignalEngine.generate — auto-detect mode and combine edges."""

import numpy as np
import pandas as pd
import pytest

from markov.engine import SignalEngine


def _series(rets):
    p = [100.0]
    for r in rets:
        p.append(p[-1] * (1 + r))
    return np.array(p)


def _panel(T=200, N=6, seed=0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.01, (T, N))
    prices = 100 * np.cumprod(1 + rets, axis=0)
    volume = np.full_like(prices, 1e6)
    dates = pd.bdate_range("2015-01-01", periods=T).to_numpy()
    return prices, volume, dates


def test_single_series_uses_time_series_mode():
    dates = pd.bdate_range("2015-01-01", periods=61).to_numpy()
    sig = SignalEngine().generate(_series(np.full(60, 0.01)), dates=dates)
    assert sig.mode == "time-series"
    assert sig.low_confidence is True
    assert len(sig.breakdown) >= 2


def test_panel_uses_cross_sectional_mode():
    prices, volume, dates = _panel()
    sig = SignalEngine().generate(prices, dates=dates, target_idx=0,
                                  volume=volume, ticker="AAA")
    assert sig.mode == "cross-sectional"
    assert sig.low_confidence is False
    assert sig.ticker == "AAA"
    # reversal/amihud/resmom should all be present
    assert {"reversal", "amihud", "resmom"} <= set(sig.breakdown)


def test_cross_sectional_recent_loser_tilts_buy():
    prices, volume, dates = _panel()
    prices[-11:, 0] *= np.linspace(1.0, 0.75, 11)  # column 0 = recent loser
    sig = SignalEngine().generate(prices, dates=dates, target_idx=0,
                                  volume=volume)
    assert sig.breakdown["reversal"] > 0


def test_panel_without_target_raises():
    prices, volume, dates = _panel()
    with pytest.raises(ValueError):
        SignalEngine().generate(prices, dates=dates, volume=volume)


def test_position_within_unit_range_and_label_consistent():
    prices, volume, dates = _panel()
    sig = SignalEngine().generate(prices, dates=dates, target_idx=2,
                                  volume=volume)
    assert -1.0 <= sig.position <= 1.0
    assert sig.label in {"BUY", "SELL", "HOLD"}
