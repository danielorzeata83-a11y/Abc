"""Tests for the Markov strategy adapter used by the backtest.

markov_strategy(past_prices) classifies states from the past, builds the
transition matrix from the past only, reads today's state, and returns
the signal P(bull)-P(bear) as a target position.
"""

import numpy as np
import pytest

from markov.strategy import make_markov_strategy


def _prices_from_daily_returns(returns):
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1.0 + r))
    return np.array(prices)


def test_returns_position_in_unit_range():
    strat = make_markov_strategy(window=20, threshold=0.05)
    prices = _prices_from_daily_returns(list(np.random.normal(0, 0.02, 100)))
    pos = strat(prices)
    assert -1.0 <= pos <= 1.0


def test_strong_bull_history_gives_long_bias():
    # Persistent uptrend -> today bull -> bull-sticky -> positive signal.
    strat = make_markov_strategy(window=20, threshold=0.05)
    prices = _prices_from_daily_returns([0.01] * 120)
    assert strat(prices) > 0


def test_strong_bear_history_gives_short_bias():
    strat = make_markov_strategy(window=20, threshold=0.05)
    prices = _prices_from_daily_returns([-0.01] * 120)
    assert strat(prices) < 0


def test_insufficient_history_returns_flat():
    strat = make_markov_strategy(window=20, threshold=0.05)
    prices = _prices_from_daily_returns([0.01] * 10)  # < window
    assert strat(prices) == 0.0
