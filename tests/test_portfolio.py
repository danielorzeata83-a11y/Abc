"""Tests for combining alpha streams at equal risk.

Blend several return streams so each contributes equal volatility
(inverse-vol weights estimated on PAST data only), then scale to a target.
The diversification benefit: combining uncorrelated positive-Sharpe
streams yields higher Sharpe than any single one.
"""

import numpy as np
import pytest

from markov.portfolio import combine_alphas


def test_combined_length_matches_inputs():
    a = np.random.default_rng(0).normal(0, 0.01, 500)
    b = np.random.default_rng(1).normal(0, 0.01, 500)
    c = combine_alphas([a, b], target_vol=0.1)
    assert len(c) == 500


def test_uncorrelated_equal_streams_raise_sharpe():
    rng = np.random.default_rng(0)
    # Two independent streams with the same modest positive Sharpe.
    a = rng.normal(0.0004, 0.01, 4000)
    b = rng.normal(0.0004, 0.01, 4000)
    def sharpe(x): return x.mean() / x.std() * np.sqrt(252)
    combo = combine_alphas([a, b], target_vol=0.1)
    # Combined Sharpe should exceed each single stream (diversification).
    assert sharpe(combo) > max(sharpe(a), sharpe(b))


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        combine_alphas([np.zeros(10), np.zeros(11)], target_vol=0.1)
