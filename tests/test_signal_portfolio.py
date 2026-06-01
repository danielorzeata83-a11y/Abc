"""Tests for the combined-signal portfolio backtest (shared by validators)."""

import numpy as np
import pytest

from markov.signal_portfolio import signal_portfolio_returns


def _mean_reverting_panel(T=400, N=8, seed=0):
    rng = np.random.default_rng(seed)
    rets = np.zeros((T, N))
    state = rng.normal(0, 0.01, N)
    for t in range(T):
        state = -0.4 * state + rng.normal(0, 0.01, N)
        rets[t] = state
    prices = 100 * np.cumprod(1 + rets, axis=0)
    volume = np.full((T, N), 1e6)
    return prices, volume


def test_returns_series_length_reasonable():
    prices, volume = _mean_reverting_panel()
    r = signal_portfolio_returns(prices, volume, holding=5)
    assert 0 < len(r) < prices.shape[0]


def test_works_without_volume():
    prices, _ = _mean_reverting_panel()
    r = signal_portfolio_returns(prices, volume=None, holding=5)
    assert np.all(np.isfinite(r))


def test_costs_reduce_performance():
    prices, volume = _mean_reverting_panel()
    g = np.prod(1 + signal_portfolio_returns(prices, volume, cost=0.0))
    n = np.prod(1 + signal_portfolio_returns(prices, volume, cost=0.005))
    assert n < g


def test_dollar_neutral_weights_small_net_exposure():
    # The book is built dollar-neutral; a flat market shouldn't dominate.
    prices, volume = _mean_reverting_panel()
    r = signal_portfolio_returns(prices, volume, holding=5)
    assert abs(np.mean(r)) < 0.05


def test_rev_sign_flips_book():
    # Momentum (rev_sign=+1) should be the opposite book of reversal (-1)
    # on the reversal leg -> different return stream.
    prices, volume = _mean_reverting_panel()
    rev = signal_portfolio_returns(prices, None, holding=5, rev_sign=-1)
    mom = signal_portfolio_returns(prices, None, holding=5, rev_sign=+1)
    assert not np.allclose(rev, mom)
