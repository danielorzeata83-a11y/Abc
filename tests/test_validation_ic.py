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


def test_correlation_and_families():
    x = np.arange(40.0)
    feats = {"a": x, "b": 2 * x + 1, "c": np.sin(x)}
    names, corr = ic.correlation_matrix(feats)
    i, j = names.index("a"), names.index("b")
    assert corr[i, j] > 0.99
    fams = ic.cluster_families(names, corr, thr=0.9)
    assert any({"a", "b"} <= set(f) for f in fams)


def test_marginal_ic_of_duplicate_is_zero():
    rng = np.random.default_rng(1)
    base = rng.normal(size=200)
    fwd = base + rng.normal(size=200) * 0.1
    feats = {"x": base, "x_copy": base.copy()}
    marg = ic.marginal_ic(feats, fwd)
    assert abs(marg["x_copy"]) < 0.1
