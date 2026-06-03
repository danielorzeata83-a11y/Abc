import numpy as np
from markov.validation import ic


def test_spearman_ic_monotonic():
    x = np.arange(20.0)
    assert ic.spearman_ic(x, x) > 0.999
    assert ic.spearman_ic(x, -x) < -0.999


def test_spearman_ic_ignores_nan_and_noise():
    rng = np.random.default_rng(0)
    s = rng.normal(size=300); r = rng.normal(size=300)
    val = ic.spearman_ic(s, r)
    assert abs(val) < 0.2
    s2 = s.copy(); s2[:5] = np.nan
    assert np.isfinite(ic.spearman_ic(s2, r))


def test_ic_decay_per_horizon():
    x = np.arange(50.0)
    returns_by_h = {1: x, 5: -x}
    d = ic.ic_decay(x, returns_by_h)
    assert d[1] > 0.99 and d[5] < -0.99


def test_pooled_ic_mean_std():
    out = ic.pooled_ic([0.1, 0.2, np.nan, 0.3])
    assert abs(out["mean"] - 0.2) < 1e-9
    assert out["n"] == 3
    assert out["std"] > 0
