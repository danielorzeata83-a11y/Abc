import numpy as np
from markov.validation import dataset


def test_forward_returns_horizons_and_tail_nan():
    close = np.array([100.0, 110, 121, 133.1])
    out = dataset.forward_returns(close, horizons=(1, 2))
    assert np.isclose(out[1][0], 0.10)
    assert np.isnan(out[1][-1])
    assert np.isclose(out[2][0], 0.21)
    assert np.isnan(out[2][-1]) and np.isnan(out[2][-2])


import pandas as pd
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import tier1


def _seed(dirpath, symbol, n=300):
    idx = pd.date_range("2025-01-02 09:30", periods=n, freq="15min")
    rng = np.random.default_rng(1)
    close = 100 + np.cumsum(rng.normal(0, 0.2, size=n))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_build_panel_aligns_features_and_returns(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    panel = dataset.build_panel(["AAA", "BBB"], d, tier1.INDICATORS,
                                horizon_tf="1day", horizons=(1, 5))
    assert set(panel.symbols) == {"AAA", "BBB"}
    feats = panel.features["AAA"]
    assert "hurst" in feats
    nbars = len(panel.close["AAA"])
    assert len(feats["hurst"]) == nbars
    assert len(panel.returns["AAA"][1]) == nbars


def test_build_panel_missing_symbol_raises(tmp_path):
    import pytest
    with pytest.raises(dataset.DataUnavailable):
        dataset.build_panel(["NOPE"], str(tmp_path), tier1.INDICATORS)
