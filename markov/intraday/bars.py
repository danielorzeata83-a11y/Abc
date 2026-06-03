"""Intraday OHLCV bars + pure timeframe resampling (15m -> 30m/1h/4h/1day).

Coarser timeframes are DERIVED locally by OHLC aggregation of the 15-min bars
(open=first, high=max, low=min, close=last, volume=sum) -- never fetched.
Timestamps are US/Eastern wall-clock (as Alpha Vantage returns intraday).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Bars:
    timestamps: np.ndarray   # datetime64[ns], sorted ascending
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    def __len__(self):
        return len(self.timestamps)

    def to_frame(self):
        return pd.DataFrame(
            {"open": self.open, "high": self.high, "low": self.low,
             "close": self.close, "volume": self.volume},
            index=pd.DatetimeIndex(self.timestamps, name="timestamp"),
        )

    @classmethod
    def from_frame(cls, df):
        idx = pd.DatetimeIndex(df.index)
        return cls(
            timestamps=idx.to_numpy(),
            open=df["open"].to_numpy(float),
            high=df["high"].to_numpy(float),
            low=df["low"].to_numpy(float),
            close=df["close"].to_numpy(float),
            volume=df["volume"].to_numpy(float),
        )


_AGG = {"open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"}

# Session opens at 09:30 ET = 570 minutes from midnight; anchor sub-day
# resamples to that so the first bucket label is always 09:30.
_SESSION_OFFSET = "570min"
_RULES = {"30m": "30min", "1h": "60min", "1day": "1D"}


def resample(bars, tf):
    """Resample 15m Bars to a coarser timeframe. '15m' is a passthrough."""
    if tf == "15m":
        return bars
    if tf == "4h":
        return resample_4h(bars)
    if tf not in _RULES:
        raise ValueError(f"unknown timeframe: {tf}")
    rule = _RULES[tf]
    # For intraday rules (sub-day), anchor buckets to session open (09:30).
    # For daily, use default alignment (calendar day).
    if tf == "1day":
        df = bars.to_frame().resample(rule, label="left", closed="left").agg(_AGG)
    else:
        df = bars.to_frame().resample(
            rule, label="left", closed="left", offset=_SESSION_OFFSET
        ).agg(_AGG)
    df = df.dropna(subset=["open", "high", "low", "close"])
    return Bars.from_frame(df)


def resample_4h(bars):
    """Session-anchored 4h buckets from 09:30 ET: two buckets/day
    ([09:30-13:30], [13:30-16:00]); the second is short (2.5h)."""
    df = bars.to_frame()
    idx = df.index
    minutes = idx.hour * 60 + idx.minute - (9 * 60 + 30)
    bucket = np.clip(np.asarray(minutes) // 240, 0, None)
    session = idx.normalize()
    agg = df.groupby([session, bucket]).agg(_AGG)
    sessions = pd.DatetimeIndex(agg.index.get_level_values(0))
    buckets = np.asarray(agg.index.get_level_values(1)).astype(int)
    anchor = sessions + pd.to_timedelta(9 * 60 + 30 + buckets * 240, unit="m")
    agg.index = pd.DatetimeIndex(anchor)
    agg = agg.sort_index()
    return Bars.from_frame(agg)
