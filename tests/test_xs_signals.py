"""Tests for cross-sectional latest-position signals.

Given a panel (T, N) and a target column, each returns the target's
position in [-1, 1] from its cross-sectional rank on the latest bar
(no look-ahead). direction=+1 -> long high score, -1 -> long low score.
"""

import numpy as np
import pytest

from markov.xs_signals import (
    rank_position,
    reversal_position,
    amihud_position,
    resmom_position,
)


def test_rank_position_extremes_and_center():
    scores = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    # highest score, direction +1 -> ~+1
    assert rank_position(scores, 4, direction=+1) == pytest.approx(1.0)
    assert rank_position(scores, 0, direction=+1) == pytest.approx(-1.0)
    # middle -> ~0
    assert abs(rank_position(scores, 2, direction=+1)) < 1e-9
    # direction flips sign
    assert rank_position(scores, 4, direction=-1) == pytest.approx(-1.0)


def _panel(T=80, N=6, seed=0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.01, (T, N))
    return 100 * np.cumprod(1 + rets, axis=0), rng


def test_reversal_position_positive_for_recent_loser():
    prices, _ = _panel()
    # Force the last column to be a big recent loser.
    prices[-11:, 0] *= np.linspace(1.0, 0.8, 11)
    pos = reversal_position(prices, target_idx=0, lookback=10)
    assert pos > 0  # loser -> buy


def test_amihud_position_in_unit_range():
    prices, _ = _panel()
    volume = np.full_like(prices, 1e6)
    volume[:, 1] = 1e4  # column 1 illiquid
    pos = amihud_position(prices, volume, target_idx=1, window=20)
    assert -1.0 <= pos <= 1.0
    assert pos > 0  # illiquid -> long


def test_resmom_position_in_unit_range():
    prices, _ = _panel(T=200)
    pos = resmom_position(prices, target_idx=0, lookback=126, skip=21)
    assert -1.0 <= pos <= 1.0


def test_reversal_rejects_bad_target():
    prices, _ = _panel()
    with pytest.raises(IndexError):
        reversal_position(prices, target_idx=99, lookback=10)
