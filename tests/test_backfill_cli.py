"""Teste pentru backfill_cli cu provider fals (fara retea)."""

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.bars import Bars
from markov.intraday.cache import read_bars
import backfill_cli


class _FakeProvider:
    def __init__(self, fail_after=None):
        self.calls = []
        self.fail_after = fail_after

    def fetch_month(self, symbol, month):
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise DataUnavailable("throttled (limita zilnica)")
        self.calls.append((symbol, month))
        idx = pd.date_range(f"{month}-01 09:30", periods=5, freq="15min")
        c = np.arange(1.0, 6.0)
        return Bars(idx.to_numpy(), c, c + 1, c - 1, c, np.full(5, 1.0))


def test_backfill_writes_cache(tmp_path):
    prov = _FakeProvider()
    n = backfill_cli.run_backfill(["AAA"], 2, str(tmp_path), prov,
                                  now=pd.Timestamp("2025-03-15"),
                                  sleeper=lambda s: None)
    assert n == 2                                   # 2 luni, 2 apeluri
    bars = read_bars(str(tmp_path), "AAA")
    assert bars is not None and len(bars) == 10     # 2 luni x 5 bare, dedup/sort


def test_backfill_stops_gracefully_on_throttle(tmp_path):
    prov = _FakeProvider(fail_after=1)              # pica la al 2-lea apel
    n = backfill_cli.run_backfill(["AAA", "BBB"], 2, str(tmp_path), prov,
                                  now=pd.Timestamp("2025-03-15"),
                                  sleeper=lambda s: None)
    assert n == 1                                   # un apel reusit inainte de throttle
    assert read_bars(str(tmp_path), "AAA") is not None   # datele aduse raman
    assert read_bars(str(tmp_path), "BBB") is None       # nu s-a ajuns la BBB


class _FakeDailyProvider:
    def __init__(self, fail_after=None):
        self.calls = []
        self.fail_after = fail_after

    def fetch(self, symbol):
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise DataUnavailable("throttled (limita zilnica)")
        self.calls.append(symbol)
        idx = pd.date_range("2024-01-02", periods=300, freq="B")   # ani de daily
        c = 100 + np.arange(300, dtype=float)
        return Bars(idx.to_numpy(), c, c + 1, c - 1, c, np.full(300, 1.0))


def test_backfill_daily_one_call_per_symbol(tmp_path):
    prov = _FakeDailyProvider()
    n = backfill_cli.run_backfill_daily(["AAA", "BBB"], str(tmp_path), prov,
                                        sleeper=lambda s: None)
    assert n == 2                                   # un apel/simbol
    assert len(read_bars(str(tmp_path), "AAA")) == 300
    assert len(read_bars(str(tmp_path), "BBB")) == 300


def test_backfill_daily_stops_on_throttle(tmp_path):
    prov = _FakeDailyProvider(fail_after=1)
    n = backfill_cli.run_backfill_daily(["AAA", "BBB"], str(tmp_path), prov,
                                        sleeper=lambda s: None)
    assert n == 1
    assert read_bars(str(tmp_path), "AAA") is not None
    assert read_bars(str(tmp_path), "BBB") is None
