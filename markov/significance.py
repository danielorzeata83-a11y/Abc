"""Permutation significance test (Step 11).

Question: does a position series have genuine predictive timing, or could
its performance arise by chance? The statistic is the mean of
position[t] * forward_return[t] (the average daily strategy return,
ignoring costs and compounding). We compare the observed statistic to a
null distribution built by shuffling the forward returns, which destroys
any real timing relationship while preserving the marginal distributions.

p_value = fraction of shuffled statistics >= observed (one-sided).
A small p_value means the timing is unlikely to be luck.
"""

import numpy as np


def _statistic(positions, returns):
    return float(np.mean(positions * returns))


def permutation_test(positions, returns, n_perm=1000, seed=None):
    """One-sided permutation test for predictive alignment.

    Returns dict with observed statistic, p_value, and null mean/std.
    """
    positions = np.asarray(positions, dtype=float)
    returns = np.asarray(returns, dtype=float)
    if len(positions) != len(returns):
        raise ValueError("positions and returns must have the same length")

    observed = _statistic(positions, returns)

    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for k in range(n_perm):
        shuffled = rng.permutation(returns)
        null[k] = _statistic(positions, shuffled)

    # One-sided: how often does random timing match or beat the observed?
    p_value = float((np.sum(null >= observed) + 1) / (n_perm + 1))

    return {
        "observed": observed,
        "p_value": p_value,
        "null_mean": float(null.mean()),
        "null_std": float(null.std()),
    }
