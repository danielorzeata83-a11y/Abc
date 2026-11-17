import numpy as np
from markov.intraday.bars import Bars
from markov.validation import tier1


def _bars(n=260):
    rng = np.random.default_rng(0)
    ts = np.arange(n).astype("datetime64[D]")
    close = 100 + np.cumsum(rng.normal(0, 1, size=n))
    o = close + rng.normal(0, 0.1, size=n)
    h = np.maximum(o, close) + np.abs(rng.normal(0, 0.2, size=n))
    l = np.minimum(o, close) - np.abs(rng.normal(0, 0.2, size=n))
    v = np.abs(rng.normal(1e6, 1e5, size=n))
    return Bars(ts, o, h, l, close, v)


def test_indicators_dict_has_expected_keys():
    assert "jump" in tier1.INDICATORS and "jump_ratio" in tier1.INDICATORS
    assert len(tier1.INDICATORS) >= 14


def test_every_adapter_returns_aligned_series():
    b = _bars()
    for name, fn in tier1.INDICATORS.items():
        out = fn(b)
        assert isinstance(out, np.ndarray), name
        assert len(out) == len(b), name
