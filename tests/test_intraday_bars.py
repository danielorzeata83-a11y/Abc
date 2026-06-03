"""Intraday Bars + pure resampling."""

import numpy as np
import pandas as pd
import pytest

from markov.intraday.bars import Bars, resample, resample_4h


def _bars(timestamps, o, h, l, c, v):
    return Bars(np.array(timestamps, dtype="datetime64[ns]"),
                np.array(o, float), np.array(h, float), np.array(l, float),
                np.array(c, float), np.array(v, float))


def _session_15m(date="2025-07-03"):
    # 26 fifteen-min bars, 09:30..15:45 ET (regular US session)
    idx = pd.date_range(f"{date} 09:30", f"{date} 15:45", freq="15min")
    n = len(idx)
    o = np.arange(n, dtype=float) + 100
    h = o + 1.0
    low = o - 1.0
    c = o + 0.5
    v = np.full(n, 10.0)
    return Bars(idx.to_numpy(), o, h, low, c, v), idx


def test_roundtrip_frame():
    b, _ = _session_15m()
    b2 = Bars.from_frame(b.to_frame())
    assert len(b2) == len(b)
    assert np.allclose(b2.close, b.close)
    assert np.array_equal(b2.timestamps, b.timestamps)


def test_15m_passthrough():
    b, _ = _session_15m()
    assert resample(b, "15m") is b


def test_resample_1h_aggregates_four_bars():
    # first hour: bars at 09:30,09:45,10:00,10:15 -> one 1h candle
    b, idx = _session_15m()
    out = resample(b, "1h")
    f = out.to_frame()
    first = f.iloc[0]
    # open=first bar open (100), high=max of the 4 highs, low=min, close=last close
    assert first["open"] == pytest.approx(100.0)
    assert first["high"] == pytest.approx(b.high[:4].max())
    assert first["low"] == pytest.approx(b.low[:4].min())
    assert first["close"] == pytest.approx(b.close[3])
    assert first["volume"] == pytest.approx(40.0)


def test_resample_1day_one_candle_per_session():
    b, _ = _session_15m()
    out = resample(b, "1day")
    assert len(out) == 1
    assert out.open[0] == pytest.approx(b.open[0])
    assert out.close[0] == pytest.approx(b.close[-1])
    assert out.high[0] == pytest.approx(b.high.max())
    assert out.volume[0] == pytest.approx(b.volume.sum())


def test_resample_4h_two_buckets_second_is_short():
    b, _ = _session_15m()
    out = resample_4h(b)
    # 09:30->13:30 (16 bars) and 13:30->16:00 (10 bars) -> exactly 2 buckets
    assert len(out) == 2
    assert out.close[-1] == pytest.approx(b.close[-1])     # session close
    assert out.open[0] == pytest.approx(b.open[0])         # session open


def test_resample_4h_no_cross_day_bleed():
    b1, _ = _session_15m("2025-07-03")
    b2, _ = _session_15m("2025-07-07")
    b = Bars(np.concatenate([b1.timestamps, b2.timestamps]),
             np.concatenate([b1.open, b2.open]), np.concatenate([b1.high, b2.high]),
             np.concatenate([b1.low, b2.low]), np.concatenate([b1.close, b2.close]),
             np.concatenate([b1.volume, b2.volume]))
    out = resample_4h(b)
    assert len(out) == 4   # 2 buckets per day, 2 days


def test_unknown_tf_raises():
    b, _ = _session_15m()
    with pytest.raises(ValueError):
        resample(b, "7m")
