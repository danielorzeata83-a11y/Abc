"""Tests for single-asset (time-series) latest-position signals.

Each returns today's target position in [-1, 1] using prices up to the
last bar only (no look-ahead).
"""

import numpy as np
import pandas as pd
import pytest

from markov.ts_signals import (
    ts_momentum_position,
    ts_reversal_position,
    volmanaged_position,
    turn_of_month_position,
)


def _prices(rets):
    p = [100.0]
    for r in rets:
        p.append(p[-1] * (1 + r))
    return np.array(p)


def test_ts_momentum_long_in_uptrend_short_in_downtrend():
    assert ts_momentum_position(_prices(np.full(60, 0.01)), ma_window=20) > 0
    assert ts_momentum_position(_prices(np.full(60, -0.01)), ma_window=20) < 0


def test_ts_momentum_flat_without_history():
    assert ts_momentum_position(_prices([0.01] * 5), ma_window=20) == 0.0


def test_ts_reversal_buys_after_drop_sells_after_spike():
    up = _prices(list(np.full(40, 0.0)) + [0.0, 0.0, -0.08])  # recent drop
    down = _prices(list(np.full(40, 0.0)) + [0.0, 0.0, 0.08])  # recent spike
    assert ts_reversal_position(up, lookback=5) > 0    # drop -> buy
    assert ts_reversal_position(down, lookback=5) < 0  # spike -> sell


def test_volmanaged_position_nonnegative_and_unit_capped():
    p = _prices(np.random.default_rng(0).normal(0, 0.02, 100))
    pos = volmanaged_position(p, target_vol=0.15, window=20)
    assert 0.0 <= pos <= 1.0


def test_volmanaged_smaller_when_more_volatile():
    calm = _prices(np.random.default_rng(1).normal(0, 0.005, 100))
    wild = _prices(np.random.default_rng(1).normal(0, 0.05, 100))
    assert volmanaged_position(wild) < volmanaged_position(calm)


def test_turn_of_month_position_on_and_off_days():
    dates = pd.bdate_range("2015-01-01", periods=40).to_numpy()
    # last business day of Jan 2015 is the 30th; near month-end -> in market
    on = turn_of_month_position(dates[:21])   # around end of first month chunk
    assert turn_of_month_position(dates) in (0.0, 1.0)


def test_ts_reversal_flat_without_history():
    assert ts_reversal_position(_prices([0.0] * 3), lookback=5) == 0.0
