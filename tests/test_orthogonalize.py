"""Tests for orthogonalising one return stream against others.

To check that a new sleeve adds INDEPENDENT information, regress it on the
existing sleeves and keep the residual. A positive-Sharpe residual means
genuine diversification, not redundancy. Betas are estimated on the data
provided (use a train slice for strict OOS use).
"""

import numpy as np
import pytest

from markov.portfolio import orthogonalize


def test_residual_is_uncorrelated_to_basis():
    rng = np.random.default_rng(0)
    base = rng.normal(0, 0.01, 2000)
    # stream = 0.7*base + independent noise
    indep = rng.normal(0.0002, 0.01, 2000)
    stream = 0.7 * base + indep
    resid = orthogonalize(stream, [base])
    # Residual should be ~uncorrelated with the basis.
    assert abs(np.corrcoef(resid, base)[0, 1]) < 0.05


def test_redundant_stream_residual_near_zero_mean_signal():
    rng = np.random.default_rng(1)
    base = rng.normal(0.0003, 0.01, 2000)
    stream = 2.0 * base  # perfectly explained by base
    resid = orthogonalize(stream, [base])
    assert np.allclose(resid, 0.0, atol=1e-10)


def test_length_preserved_and_multiple_basis():
    rng = np.random.default_rng(2)
    a = rng.normal(0, 0.01, 500)
    b = rng.normal(0, 0.01, 500)
    s = rng.normal(0, 0.01, 500)
    resid = orthogonalize(s, [a, b])
    assert len(resid) == 500
    assert abs(np.corrcoef(resid, a)[0, 1]) < 0.1
    assert abs(np.corrcoef(resid, b)[0, 1]) < 0.1


def test_rejects_length_mismatch():
    with pytest.raises(ValueError):
        orthogonalize(np.zeros(10), [np.zeros(11)])
