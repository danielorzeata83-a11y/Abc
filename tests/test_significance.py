"""Tests for the permutation significance test (Step 11).

We test whether a position series has genuine predictive alignment with
the returns it earns, versus random chance. The statistic is the mean of
position[t] * forward_return[t]. The null distribution is built by
shuffling the forward returns (destroying any timing relationship) and
recomputing the statistic.
"""

import numpy as np
import pytest

from markov.significance import permutation_test


def test_perfect_predictor_is_significant():
    rng = np.random.default_rng(0)
    rets = rng.normal(0, 0.02, 500)
    positions = np.sign(rets)  # cheating predictor: always right
    res = permutation_test(positions, rets, n_perm=500, seed=1)
    assert res["observed"] > 0
    assert res["p_value"] < 0.01


def test_random_positions_not_significant():
    rng = np.random.default_rng(2)
    rets = rng.normal(0, 0.02, 500)
    positions = rng.choice([-1.0, 1.0], size=500)  # no relation to rets
    res = permutation_test(positions, rets, n_perm=500, seed=3)
    assert res["p_value"] > 0.05


def test_anti_predictor_has_high_pvalue():
    rng = np.random.default_rng(4)
    rets = rng.normal(0, 0.02, 500)
    positions = -np.sign(rets)  # always wrong -> observed < 0
    res = permutation_test(positions, rets, n_perm=500, seed=5)
    assert res["observed"] < 0
    assert res["p_value"] > 0.95


def test_pvalue_in_unit_interval():
    rng = np.random.default_rng(6)
    rets = rng.normal(0, 0.02, 200)
    positions = rng.normal(0, 1, 200)
    res = permutation_test(positions, rets, n_perm=200, seed=7)
    assert 0.0 <= res["p_value"] <= 1.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        permutation_test(np.ones(10), np.ones(9), n_perm=10)


def test_reproducible_with_seed():
    rng = np.random.default_rng(8)
    rets = rng.normal(0, 0.02, 300)
    positions = rng.normal(0, 1, 300)
    a = permutation_test(positions, rets, n_perm=300, seed=42)
    b = permutation_test(positions, rets, n_perm=300, seed=42)
    assert a["p_value"] == b["p_value"]
