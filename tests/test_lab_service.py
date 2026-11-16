import json
import time

import numpy as np
import pandas as pd
import pytest

from markov.data_providers import DataUnavailable
from sensa.lab_service import AdjustedCache, DOC_UNIVERSE, LabService, resolve_universe

OVERVIEW = {"stocks": [
    {"ticker": "AAA", "kind": "stock", "holders": 90, "value": 5, "gone": False, "new_listing": False},
    {"ticker": "SPY", "kind": "etf", "holders": 99, "value": 9, "gone": False, "new_listing": False},
    {"ticker": "BBB", "kind": "adr", "holders": 80, "value": 4, "gone": False, "new_listing": False},
    {"ticker": "OLD", "kind": "stock", "holders": 70, "value": 3, "gone": True, "new_listing": False},
    {"ticker": "CCC", "kind": "stock", "holders": 60, "value": 2, "gone": False, "new_listing": False}]}


class Insiders:
    def trades_since(self, days):
        return [{"symbol": "XXX", "side": "buy", "value": 50000.0}, {"symbol": "YYY", "side": "buy", "value": 90000.0},
                {"symbol": "YYY", "side": "sell", "value": 99999999.0}, {"symbol": "XXX", "side": "buy", "value": 10000.0}]


def test_universe_sources_are_resolved_cleanly():
    assert resolve_universe("document") == list(DOC_UNIVERSE) and len(DOC_UNIVERSE) == 10
    assert resolve_universe("most_held", overview=OVERVIEW, n=2) == ["AAA", "BBB"]               # stocks/ADRs only, none that vanished
    assert resolve_universe("insider_buys", insiders=Insiders(), n=5) == ["YYY", "XXX"]          # by total buying, sells ignored
    assert resolve_universe("watchlist", watchlist=("AAPL", "MSFT")) == ["AAPL", "MSFT"]
    assert resolve_universe("custom", custom="aapl, msft  nvda;BAD/X,aapl") == ["AAPL", "MSFT", "NVDA"]
    for bad in (lambda: resolve_universe("nope"), lambda: resolve_universe("custom", custom="AAPL"), lambda: resolve_universe("most_held")):
        with pytest.raises((ValueError, DataUnavailable)):
            bad()


def test_adjusted_cache_downloads_once_and_survives_restarts(tmp_path):
    calls = []

    def fn(t, years):
        calls.append((t, years))
        return [("2026-01-02", 1.0), ("2026-01-03", 2.0)]
    path = str(tmp_path / "adj.json")
    c = AdjustedCache(fn, path)
    c.get("aapl", 10); c.get("AAPL", 10); c.get("AAPL", 5)
    assert calls == [("AAPL", 10), ("AAPL", 5)]
    again = AdjustedCache(lambda t, y: (_ for _ in ()).throw(AssertionError("network")), path)
    assert again.get("AAPL", 10) == [("2026-01-02", 1.0), ("2026-01-03", 2.0)]


def make_history(n=900, seed=0):
    rng = np.random.default_rng(seed)
    idx = [pd.Timestamp((20000 + i) * 86400, unit="s").strftime("%Y-%m-%d") for i in range(n)]

    def fn(t, years):
        r = np.random.default_rng(abs(hash(t)) % 10_000 + seed).normal(0.0004, 0.012, n)
        return list(zip(idx, 100 * np.cumprod(1 + r)))
    return fn


FAST = {"window": 200, "every": 21, "lam_grid": [3.0], "kappa_grid": [0.005], "cvar_lam_grid": [1.0], "cvar_iters": 200, "perturbations": 3}


def test_a_run_is_executed_in_the_background_saved_and_listed(tmp_path):
    svc = LabService(str(tmp_path), make_history(), min_rows=500)
    rid = svc.submit({"universe": "custom", "custom": "AAA BBB CCC DDD", "years": 10, "config": FAST})
    svc.wait(120)
    assert svc.status()["state"] == "done" and svc.status()["run_id"] == rid
    runs = svc.runs()
    assert runs[0]["id"] == rid and runs[0]["tickers"] == ["AAA", "BBB", "CCC", "DDD"] and "passed" in runs[0]
    r = svc.result(rid)
    assert r["tickers"] == ["AAA", "BBB", "CCC", "DDD"] and set(r["test"]["models"]) >= {"equal_weight", "extended"}
    assert svc.file(rid, "report.md").endswith("report.md")
    with pytest.raises(KeyError):
        svc.result("../../etc/passwd")
    with pytest.raises(KeyError):
        svc.file(rid, "../result.json")


def test_a_second_submission_while_running_is_refused_and_failures_are_reported(tmp_path):
    def slow(t, years):
        time.sleep(0.4)
        raise DataUnavailable("no data")
    svc = LabService(str(tmp_path), slow, min_rows=500)
    svc.submit({"universe": "custom", "custom": "AAA BBB"})
    with pytest.raises(RuntimeError, match="already running"):
        svc.submit({"universe": "custom", "custom": "AAA BBB"})
    svc.wait(30)
    assert svc.status()["state"] == "error" and "at least two" in svc.status()["message"] and svc.runs() == []


def test_spec_values_are_validated(tmp_path):
    svc = LabService(str(tmp_path), make_history(), min_rows=500)
    for spec in ({"universe": "custom", "custom": "AAA BBB", "years": 99}, {"universe": "custom", "custom": "AAA BBB", "cost_bps": -1},
                 {"universe": "custom", "custom": "AAA BBB", "cap": 0.01}, {"universe": "custom", "custom": "AAA BBB", "config": {"window": 5}}):
        with pytest.raises(ValueError):
            svc.submit(spec)


def test_adjusted_cache_retries_a_throttled_download_with_backoff_and_then_gives_up(tmp_path):
    naps, calls = [], []

    def flaky(t, years):
        calls.append(t)
        if len(calls) < 3:
            raise DataUnavailable("HTTP 429")
        return [("2026-01-02", 1.0)]
    c = AdjustedCache(flaky, str(tmp_path / "a.json"), sleep=naps.append, retries=2, backoff=1.5, spacing=0.25)
    assert c.get("X", 10) == [("2026-01-02", 1.0)] and len(calls) == 3
    assert naps[:2] == [1.5, 3.0] and naps[-1] == 0.25          # exponential backoff, then a pause before the next ticker

    def dead(t, years):
        raise DataUnavailable("blocked")
    d = AdjustedCache(dead, str(tmp_path / "b.json"), sleep=lambda s: None, retries=2)
    with pytest.raises(DataUnavailable, match="blocked"):
        d.get("Y", 10)
