"""Tests for the Amihud illiquidity factor (market-neutral).

Amihud (2002) illiquidity = average of |return| / dollar-volume. Less
liquid names command a return premium. As a dollar-neutral long-short
(long illiquid, short liquid) it is a fifth alpha source, independent of
reversal/calendar/vol-managed.

Panel convention: prices and volume have shape (T, N); decisions at day t
use data up to t only.
"""

import numpy as np
import pytest

from markov.amihud import xs_amihud_returns, illiquidity_scores


def _panel(T=400, N=10, seed=0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.012, (T, N))
    prices = 100 * np.cumprod(1 + rets, axis=0)
    # Half the names are illiquid (low volume) AND earn a bit more.
    base_vol = np.concatenate([np.full(N // 2, 1e5), np.full(N - N // 2, 1e7)])
    volume = base_vol[None, :] * rng.uniform(0.5, 1.5, (T, N))
    return prices, volume


def test_scores_finite_and_per_asset():
    prices, volume = _panel()
    s = illiquidity_scores(prices, volume, t=100, window=20)
    assert len(s) == prices.shape[1]
    assert np.all(np.isfinite(s))


def test_illiquid_names_score_higher():
    prices, volume = _panel()
    s = illiquidity_scores(prices, volume, t=200, window=20)
    # First half (low volume) should be more illiquid (higher score).
    assert np.nanmean(s[:5]) > np.nanmean(s[5:])


def test_costs_reduce_performance():
    prices, volume = _panel()
    g = np.prod(1 + xs_amihud_returns(prices, volume, cost=0.0))
    n = np.prod(1 + xs_amihud_returns(prices, volume, cost=0.002))
    assert n < g


def test_returns_length_no_lookahead():
    prices, volume = _panel()
    r = xs_amihud_returns(prices, volume, window=20, holding=21)
    assert len(r) < prices.shape[0]


def test_rejects_window_too_large():
    prices, volume = _panel(T=15)
    with pytest.raises(ValueError):
        xs_amihud_returns(prices, volume, window=60)
