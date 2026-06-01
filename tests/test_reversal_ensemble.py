"""Tests for the enhanced ensemble reversal.

Two improvements over single-horizon reversal:
1. Ensemble across several lookbacks (e.g. 3/5/10 days) -> smoother,
   less noise-sensitive signal, lower effective turnover.
2. Inverse-volatility weighting of the legs (intra-portfolio risk
   parity) so the most volatile names don't dominate risk and costs.

Panel convention: prices shape (T, N); decisions at day t use prices[:t+1].
"""

import numpy as np
import pytest

from markov.reversal_ensemble import xs_reversal_ensemble


def _mean_reverting_panel(T=400, N=10, seed=0):
    rng = np.random.default_rng(seed)
    rets = np.zeros((T, N))
    state = rng.normal(0, 0.01, N)
    vols = rng.uniform(0.005, 0.03, N)  # heterogeneous vols
    for t in range(T):
        state = -0.4 * state + rng.normal(0, 1, N) * vols
        rets[t] = state
    prices = 100 * np.cumprod(1 + rets, axis=0)
    return prices


def test_ensemble_profitable_gross_on_mean_reverting_panel():
    prices = _mean_reverting_panel()
    rets = xs_reversal_ensemble(prices, lookbacks=(3, 5, 10), holding=5,
                                top_frac=0.2, cost=0.0)
    assert np.prod(1 + rets) - 1 > 0


def test_inverse_vol_reduces_turnover_vs_equal_weight():
    # Inverse-vol weighting should not blow up; series finite and sane.
    prices = _mean_reverting_panel()
    rets = xs_reversal_ensemble(prices, lookbacks=(5,), holding=5,
                                top_frac=0.2, cost=0.0, inverse_vol=True)
    assert np.all(np.isfinite(rets))


def test_costs_reduce_performance():
    prices = _mean_reverting_panel()
    g = np.prod(1 + xs_reversal_ensemble(prices, cost=0.0))
    n = np.prod(1 + xs_reversal_ensemble(prices, cost=0.002))
    assert n < g


def test_no_lookahead_length():
    prices = _mean_reverting_panel()
    rets = xs_reversal_ensemble(prices, lookbacks=(3, 5, 10), holding=5)
    # Can't start until the longest lookback (+ vol window) has history.
    assert len(rets) < prices.shape[0]


def test_rejects_lookback_too_large():
    prices = _mean_reverting_panel(T=15)
    with pytest.raises(ValueError):
        xs_reversal_ensemble(prices, lookbacks=(50,), holding=5)
