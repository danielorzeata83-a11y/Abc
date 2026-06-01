"""Tests for residual (idiosyncratic) momentum.

Plain momentum crashes because it loads on market/factor exposure.
Residual momentum (Blitz, Huij & Martens 2011) regresses each stock on
the market, then ranks on the cumulated RESIDUAL return -- the stock's
idiosyncratic trend. Long residual winners / short residual losers. It is
market-neutral by construction and historically more robust than plain
momentum.

Panel convention: prices shape (T, N); decisions at day t use prices[:t+1].
"""

import numpy as np
import pytest

from markov.resmom import residual_momentum_scores, xs_residual_momentum_returns


def _panel_with_idio_trends(T=400, N=10, seed=0):
    rng = np.random.default_rng(seed)
    mkt = rng.normal(0.0004, 0.01, T)
    betas = rng.uniform(0.5, 1.5, N)
    rets = np.outer(mkt, betas) + rng.normal(0, 0.005, (T, N))
    # Inject idiosyncratic uptrend into the first 3 names.
    rets[:, :3] += 0.0015
    prices = 100 * np.cumprod(1 + rets, axis=0)
    return prices, mkt


def test_scores_rank_idio_winners_high():
    prices, _ = _panel_with_idio_trends()
    s = residual_momentum_scores(prices, t=300, lookback=126, skip=21)
    assert len(s) == prices.shape[1]
    # The injected idiosyncratic winners should score above the rest.
    assert np.mean(s[:3]) > np.mean(s[3:])


def test_market_neutral_profitable_on_idio_panel():
    prices, _ = _panel_with_idio_trends()
    r = xs_residual_momentum_returns(prices, lookback=126, skip=21,
                                     holding=21, cost=0.0)
    assert np.prod(1 + r) - 1 > 0


def test_costs_reduce_performance():
    prices, _ = _panel_with_idio_trends()
    g = np.prod(1 + xs_residual_momentum_returns(prices, cost=0.0))
    n = np.prod(1 + xs_residual_momentum_returns(prices, cost=0.003))
    assert n < g


def test_returns_length_no_lookahead():
    prices, _ = _panel_with_idio_trends()
    r = xs_residual_momentum_returns(prices, lookback=126, skip=21)
    assert len(r) < prices.shape[0]


def test_rejects_lookback_too_large():
    prices, _ = _panel_with_idio_trends(T=60)
    with pytest.raises(ValueError):
        xs_residual_momentum_returns(prices, lookback=126, skip=21)
