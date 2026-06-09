import numpy as np
from markov.validation import regime


def test_hurst_regime_labels_trend_vs_meanrev():
    rng = np.random.default_rng(0)
    trend = np.cumsum(np.abs(rng.normal(1.0, 0.1, size=300)))
    labels = regime.hurst_regime(trend, window=100)
    tail = labels[150:]
    assert (tail == "trend").sum() > (tail == "meanrev").sum()


def test_conditional_ic_splits_by_regime():
    sig = np.array([1.0, 2, 3, 4, 5, 6])
    fwd = np.array([1.0, 2, 3, -4, -5, -6])
    labels = np.array(["a", "a", "a", "b", "b", "b"])
    d = regime.conditional_ic(sig, fwd, labels)
    assert d["a"] > 0.99 and d["b"] < -0.99
