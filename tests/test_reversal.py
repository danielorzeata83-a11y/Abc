"""Tests for cross-sectional short-term reversal.

The complement of momentum: over short horizons (days to a week) the
biggest recent LOSERS tend to bounce and the biggest WINNERS pull back
(Lehmann 1990; Lo & MacKinlay 1990). Long losers / short winners,
rebalanced frequently. Strong precisely in trending bull markets where
long-short momentum struggles.

Panel convention: prices shape (T, N). Decisions at day t use prices[:t+1].
"""

import numpy as np
import pytest

from markov.reversal import xs_reversal_returns


def _mean_reverting_panel(T=400, N=8, seed=0):
    """Assets that oscillate: yesterday's loser tends to be tomorrow's winner."""
    rng = np.random.default_rng(seed)
    rets = np.zeros((T, N))
    state = rng.normal(0, 0.01, N)
    for t in range(T):
        # strong negative autocorrelation -> short-term reversal exists
        state = -0.4 * state + rng.normal(0, 0.01, N)
        rets[t] = state
    prices = 100 * np.cumprod(1 + rets, axis=0)
    return prices


def test_reversal_profitable_on_mean_reverting_panel():
    prices = _mean_reverting_panel()
    rets = xs_reversal_returns(prices, lookback=5, holding=1, top_frac=0.25,
                              cost=0.0)
    assert np.prod(1 + rets) - 1 > 0


def test_costs_reduce_performance():
    prices = _mean_reverting_panel()
    gross = np.prod(1 + xs_reversal_returns(prices, lookback=5, holding=1,
                                            top_frac=0.25, cost=0.0))
    net = np.prod(1 + xs_reversal_returns(prices, lookback=5, holding=1,
                                          top_frac=0.25, cost=0.001))
    assert net < gross


def test_returns_length_no_lookahead():
    prices = _mean_reverting_panel()
    rets = xs_reversal_returns(prices, lookback=5, holding=1, top_frac=0.25)
    assert len(rets) <= prices.shape[0] - 5


def test_rejects_lookback_too_large():
    prices = _mean_reverting_panel(T=10)
    with pytest.raises(ValueError):
        xs_reversal_returns(prices, lookback=50, holding=1)
