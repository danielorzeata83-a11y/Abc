import numpy as np
import pandas as pd
import pytest
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.intraday.service import (Config, get_candles, get_features, TIMEFRAMES)
from markov.data_providers import DataUnavailable


def _seed(tmp_path, symbol="NVDA", days=3):
    frames = []
    for d in range(days):
        day = pd.Timestamp("2025-07-03") + pd.Timedelta(days=d)
        idx = pd.date_range(f"{day.date()} 09:30", f"{day.date()} 15:45", freq="15min")
        n = len(idx)
        base = 100.0 + d
        o = np.linspace(base, base + 5, n)
        frames.append(pd.DataFrame({"open": o, "high": o + 1, "low": o - 1,
            "close": o + 0.5, "volume": np.full(n, 10.0)}, index=idx))
    df = pd.concat(frames); df.index.name = "timestamp"
    write_bars(str(tmp_path), symbol, Bars.from_frame(df))
    return str(tmp_path)


def test_get_candles_shape_intraday(tmp_path):
    d = _seed(tmp_path)
    out = get_candles("NVDA", "1h", d)
    assert isinstance(out, list) and out
    row = out[0]
    assert set(["time","open","high","low","close","volume"]).issubset(row)
    assert isinstance(row["time"], int)        # epoch seconds for intraday
    assert "vwap" in row                         # session vwap present intraday


def test_get_candles_daily_time_is_date_string(tmp_path):
    d = _seed(tmp_path)
    out = get_candles("NVDA", "1day", d)
    assert isinstance(out[0]["time"], str) and len(out[0]["time"]) == 10
    assert len(out) == 3                          # 3 sessions


def test_get_candles_missing_raises(tmp_path):
    with pytest.raises(DataUnavailable):
        get_candles("ZZZ", "1h", str(tmp_path))


def test_get_features_keys_and_types(tmp_path):
    d = _seed(tmp_path)
    f = get_features("NVDA", "15m", d)
    for k in ["garman_klass","rogers_satchell","realized_variance","bipower_variation",
              "jump","jump_ratio","hurst","fdi","permutation_entropy","rqa_determinism",
              "corwin_schultz","roll_measure","high_52w_proximity","max_effect"]:
        assert k in f
        assert f[k] is None or isinstance(f[k], float)


def test_get_features_missing_raises(tmp_path):
    with pytest.raises(DataUnavailable):
        get_features("ZZZ", "15m", str(tmp_path))


def test_config_from_env_tolerant():
    c = Config.from_env({"INTRADAY_WATCHLIST": "nvda, aapl ", "INTRADAY_PORT": "9000"})
    assert c.watchlist == ("NVDA", "AAPL")
    assert c.port == 9000
    c2 = Config.from_env({"INTRADAY_PORT": "notanint"})   # invalid -> default
    assert c2.port == 8765
    c3 = Config.from_env({})
    assert c3.watchlist[0] == "NVDA"
