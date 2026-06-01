"""Tests for the market-neutral low-volatility factor.

The low-vol anomaly: low-volatility stocks deliver better risk-adjusted
returns than high-vol ones. As a dollar-neutral long-short (long lowest
trailing vol, short highest), it is a second alpha source largely
independent of short-term reversal.

Panel convention: prices shape (T, N); decisions at day t use prices[:t+1].
"""

import numpy as np
import pytest

from markov.lowvol import xs_lowvol_returns, trailing_vol_scores


def _panel(T=400, N=10, seed=0):
    rng = np.random.default_rng(seed)
    vols = rng.uniform(0.005, 0.03, N)
    rets = rng.normal(0.0003, 1, (T, N)) * vols
    return 100 * np.cumprod(1 + rets, axis=0)


def test_vol_scores_rank_low_below_high():
    prices = _panel()
    s = trailing_vol_scores(prices, window=60)
    assert len(s) == prices.shape[1]
    assert np.all(np.isfinite(s))


def test_returns_length_no_lookahead():
    prices = _panel()
    rets = xs_lowvol_returns(prices, vol_window=60, holding=21, top_frac=0.2)
    assert len(rets) < prices.shape[0]


def test_costs_reduce_performance():
    prices = _panel()
    g = np.prod(1 + xs_lowvol_returns(prices, cost=0.0))
    n = np.prod(1 + xs_lowvol_returns(prices, cost=0.002))
    assert n < g


def test_rejects_window_too_large():
    prices = _panel(T=30)
    with pytest.raises(ValueError):
        xs_lowvol_returns(prices, vol_window=60)
