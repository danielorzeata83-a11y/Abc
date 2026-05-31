"""Tests for state classification (Step 1-2 of the hedge-fund method).

Spec (from the source method):
- Look back over a fixed window (default 20 trading days).
- Sum the simple daily returns over that window.
- >= +threshold (default +5%)  -> BULL
- <= -threshold (default -5%)  -> BEAR
- otherwise                    -> SIDEWAYS

The first (window) days have no full lookback and are labelled UNKNOWN.
"""

import numpy as np
import pytest

from markov.states import State, classify_states


def _prices_from_daily_returns(returns):
    """Build a price series whose simple daily returns equal `returns`."""
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1.0 + r))
    return np.array(prices)


def test_constant_one_percent_gain_is_bull():
    # 20 days of +1% => ~+22% windowed sum of returns => BULL on day 20.
    prices = _prices_from_daily_returns([0.01] * 20)
    states = classify_states(prices, window=20, threshold=0.05)
    assert states[-1] == State.BULL


def test_constant_one_percent_loss_is_bear():
    prices = _prices_from_daily_returns([-0.01] * 20)
    states = classify_states(prices, window=20, threshold=0.05)
    assert states[-1] == State.BEAR


def test_flat_market_is_sideways():
    prices = _prices_from_daily_returns([0.0] * 20)
    states = classify_states(prices, window=20, threshold=0.05)
    assert states[-1] == State.SIDEWAYS


def test_first_window_days_are_unknown():
    prices = _prices_from_daily_returns([0.01] * 25)
    states = classify_states(prices, window=20, threshold=0.05)
    # prices has 26 points -> 25 returns. The first full 20-window covers
    # returns 0..19 and labels day index 19. Days 0..18 are UNKNOWN.
    assert all(s == State.UNKNOWN for s in states[:19])
    assert states[19] != State.UNKNOWN


def test_boundary_exactly_at_threshold_is_directional():
    # Sum of returns exactly +5% should count as BULL (inclusive boundary).
    rets = [0.0025] * 20  # 20 * 0.25% = 5.0% summed
    prices = _prices_from_daily_returns(rets)
    states = classify_states(prices, window=20, threshold=0.05)
    assert states[-1] == State.BULL


def test_output_length_matches_returns_length():
    prices = _prices_from_daily_returns([0.01] * 30)
    states = classify_states(prices, window=20, threshold=0.05)
    # One state label per return (len(prices) - 1).
    assert len(states) == len(prices) - 1


def test_rejects_too_short_series():
    prices = _prices_from_daily_returns([0.01] * 5)
    with pytest.raises(ValueError):
        classify_states(prices, window=20, threshold=0.05)
