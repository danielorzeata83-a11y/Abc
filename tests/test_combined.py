"""Tests for combined strategies: regime filter as a defensive overlay.

The Markov regime is used the way it is used in practice -- not as an
entry signal, but as a RISK GATE that cuts exposure in a bear regime on
top of a base strategy (buy & hold or trend-following). All decisions
use past prices only (walk-forward safe).
"""

import numpy as np
import pytest

from markov.combined import (
    make_buy_hold_strategy,
    make_trend_strategy,
    make_regime_filtered_strategy,
)
from markov.states import State


def _prices(rets):
    p = [100.0]
    for r in rets:
        p.append(p[-1] * (1 + r))
    return np.array(p)


def test_buy_hold_always_long():
    s = make_buy_hold_strategy()
    assert s(_prices([0.01] * 50)) == 1.0
    assert s(_prices([-0.05] * 50)) == 1.0


def test_trend_long_above_ma_flat_below():
    s = make_trend_strategy(ma_window=20)
    up = _prices(np.full(40, 0.02))    # steadily rising -> price > MA
    down = _prices(np.full(40, -0.02))  # steadily falling -> price < MA
    assert s(up) == 1.0
    assert s(down) == 0.0


def test_trend_flat_without_enough_history():
    s = make_trend_strategy(ma_window=20)
    assert s(_prices([0.01] * 5)) == 0.0


def test_regime_filter_keeps_base_when_not_bear():
    # A rising series should classify recent state as BULL -> keep base.
    base = make_buy_hold_strategy()
    filtered = make_regime_filtered_strategy(
        base, window=20, threshold=0.05, bear_exposure=0.0
    )
    rising = _prices(np.full(80, 0.03))
    assert filtered(rising) == pytest.approx(1.0)


def test_regime_filter_cuts_exposure_in_bear():
    base = make_buy_hold_strategy()
    filtered = make_regime_filtered_strategy(
        base, window=20, threshold=0.05, bear_exposure=0.0
    )
    falling = _prices(np.full(80, -0.03))  # clearly bear
    assert filtered(falling) == pytest.approx(0.0)


def test_regime_filter_partial_exposure_in_bear():
    base = make_buy_hold_strategy()
    filtered = make_regime_filtered_strategy(
        base, window=20, threshold=0.05, bear_exposure=0.5
    )
    falling = _prices(np.full(80, -0.03))
    assert filtered(falling) == pytest.approx(0.5)


def test_regime_filter_passes_through_when_no_history():
    base = make_buy_hold_strategy()
    filtered = make_regime_filtered_strategy(base, window=20, threshold=0.05)
    short = _prices([0.01] * 5)
    # Not enough history to classify -> do not gate, return base position.
    assert filtered(short) == 1.0
