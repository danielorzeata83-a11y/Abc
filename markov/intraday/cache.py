"""On-disk CSV cache of 15-min Bars + refresh policy.

One CSV per symbol: <data_dir>/<SYMBOL>_15m.csv (timestamp,open,high,low,close,
volume). Only 15-min bars are stored; coarser timeframes are derived on demand.
"""

import os

import pandas as pd

from markov.intraday.bars import Bars


def cache_path(data_dir, symbol):
    return os.path.join(data_dir, f"{symbol.upper()}_15m.csv")


def read_bars(data_dir, symbol):
    path = cache_path(data_dir, symbol)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    return Bars.from_frame(df)


def write_bars(data_dir, symbol, bars):
    os.makedirs(data_dir, exist_ok=True)
    path = cache_path(data_dir, symbol)
    df = bars.to_frame()
    df.index.name = "timestamp"
    tmp = path + ".tmp"
    df.to_csv(tmp)
    os.replace(tmp, path)


def merge_bars(old, new):
    merged = pd.concat([old.to_frame(), new.to_frame()])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    return Bars.from_frame(merged)


def needs_refresh(data_dir, symbol, now, min_interval_min):
    path = cache_path(data_dir, symbol)
    if not os.path.exists(path):
        return True
    age_min = (now.timestamp() - os.path.getmtime(path)) / 60.0
    return age_min >= min_interval_min


def backfill_months(now, n):
    months, y, m = [], now.year, now.month
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(months))
