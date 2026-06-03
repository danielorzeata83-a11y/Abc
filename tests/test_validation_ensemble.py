import numpy as np
from markov.validation import ensemble


def test_zscore_causal_no_lookahead():
    rng = np.random.default_rng(0)
    x = rng.normal(size=50)
    z = ensemble.zscore_causal(x)
    x2 = x.copy(); x2[30:] += 100.0
    z2 = ensemble.zscore_causal(x2)
    assert abs(z[20] - z2[20]) < 1e-9


def test_equal_weight_is_mean_of_zscores():
    x = np.arange(30.0)
    feats = {"a": x, "b": x}
    sig = ensemble.equal_weight_signal(feats, causal=False)
    za = (x - x.mean()) / x.std()
    assert np.allclose(sig[5:], za[5:], atol=1e-9)
