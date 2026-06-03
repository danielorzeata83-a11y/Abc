"""On-disk CSV cache for 15-min bars + refresh policy."""

import os
import numpy as np
import pandas as pd
import pytest

from markov.intraday.bars import Bars
from markov.intraday.cache import (
    cache_path, read_bars, write_bars, merge_bars, needs_refresh, backfill_months)


def _bars(start, n, base=100.0):
    idx = pd.date_range(start, periods=n, freq="15min")
    o = np.arange(n, dtype=float) + base
    return Bars(idx.to_numpy(), o, o + 1, o - 1, o + 0.5, np.full(n, 10.0))


def test_write_then_read_roundtrip(tmp_path):
    b = _bars("2025-07-03 09:30", 5)
    write_bars(str(tmp_path), "NVDA", b)
    got = read_bars(str(tmp_path), "NVDA")
    assert got is not None
    assert len(got) == 5
    assert np.allclose(got.close, b.close)
    assert np.array_equal(got.timestamps, b.timestamps)


def test_read_missing_returns_none(tmp_path):
    assert read_bars(str(tmp_path), "ZZZ") is None


def test_merge_dedups_and_sorts(tmp_path):
    a = _bars("2025-07-03 09:30", 3, base=100.0)
    b = _bars("2025-07-03 10:00", 3, base=200.0)   # overlaps a's 3rd bar (10:00)
    m = merge_bars(a, b)
    f = m.to_frame()
    assert f.index.is_monotonic_increasing
    assert not f.index.has_duplicates
    # new wins on the overlapping 10:00 timestamp
    assert f.loc["2025-07-03 10:00", "close"] == pytest.approx(b.close[0])


def test_needs_refresh(tmp_path):
    import time
    assert needs_refresh(str(tmp_path), "NVDA", pd.Timestamp.now(), 30) is True
    write_bars(str(tmp_path), "NVDA", _bars("2025-07-03 09:30", 2))
    assert needs_refresh(str(tmp_path), "NVDA", pd.Timestamp.now(), 30) is False
    # simulate a stale file
    old = time.time() - 3600
    os.utime(cache_path(str(tmp_path), "NVDA"), (old, old))
    assert needs_refresh(str(tmp_path), "NVDA", pd.Timestamp.now(), 30) is True


def test_backfill_months_ascending(tmp_path):
    months = backfill_months(pd.Timestamp("2026-06-03"), 12)
    assert months[0] == "2025-07"
    assert months[-1] == "2026-06"
    assert len(months) == 12
    assert months == sorted(months)
