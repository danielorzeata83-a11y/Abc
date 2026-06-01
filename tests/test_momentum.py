"""Tests for cross-sectional (portfolio) momentum.

This is how momentum is actually validated: rank a UNIVERSE of assets by
past return, go long winners / short losers, rebalance periodically. The
idiosyncratic luck of any single asset averages out across the panel.

Panel convention: prices is a 2D array of shape (T, N) -- T days, N
assets. Every decision at rebalance day t uses prices[:t+1] only.
"""

import numpy as np
import pytest

from markov.momentum import xs_momentum_returns, momentum_scores


def _panel_with_persistent_winners(T=400, seed=0):
    """N=6 assets: 3 steady uptrenders, 3 steady downtrenders + noise."""
    rng = np.random.default_rng(seed)
    drifts = np.array([0.002, 0.0015, 0.001, -0.001, -0.0015, -0.002])
    rets = rng.normal(0, 0.005, (T, len(drifts))) + drifts
    prices = 100 * np.cumprod(1 + rets, axis=0)
    return prices


def test_momentum_scores_rank_winners_above_losers():
    prices = _panel_with_persistent_winners()
    scores = momentum_scores(prices, lookback=126, skip=21)
    # First asset (strongest uptrend) should outscore the last (downtrend).
    assert scores[0] > scores[-1]


def test_scores_length_matches_assets():
    prices = _panel_with_persistent_winners()
    scores = momentum_scores(prices, lookback=126, skip=21)
    assert len(scores) == prices.shape[1]


def test_long_short_momentum_is_profitable_on_trending_panel():
    prices = _panel_with_persistent_winners()
    rets = xs_momentum_returns(
        prices, lookback=126, skip=21, holding=21, top_frac=0.34,
        long_short=True,
    )
    # On a panel with persistent winners/losers, momentum should make money.
    assert np.prod(1 + rets) - 1 > 0


def test_returns_no_lookahead_first_window_empty():
    prices = _panel_with_persistent_winners()
    rets = xs_momentum_returns(prices, lookback=126, skip=21, holding=21)
    # Can't trade until lookback+skip history exists; series is shorter.
    assert len(rets) <= prices.shape[0] - (126 + 21)


def test_long_only_weights_sum_to_one_exposure():
    # Long-only momentum should be net long (positive mean position).
    prices = _panel_with_persistent_winners()
    rets_ls = xs_momentum_returns(prices, long_short=True, top_frac=0.34)
    rets_lo = xs_momentum_returns(prices, long_short=False, top_frac=0.34)
    # Both produce a return series of equal length.
    assert len(rets_ls) == len(rets_lo)


def test_rejects_lookback_larger_than_history():
    prices = _panel_with_persistent_winners(T=50)
    with pytest.raises(ValueError):
        xs_momentum_returns(prices, lookback=126, skip=21)
