import json
import os

import numpy as np
import pandas as pd
import pytest

from markov.data_providers import DataUnavailable
from sensa.research_job import hist_insiders, hist_overviews, research_board, signal_date_of
from tests.test_signal_history import DATES, N, SIGNAL_IDX, world


def ov(period, filed_dates):
    return {"period": period, "prev_period": "p", "quarter": period, "funds": [{"filed": d} for d in filed_dates], "stocks": []}


def test_signal_date_is_when_most_of_the_top_funds_had_filed():
    assert signal_date_of(ov("2026-06-30", ["2026-08-01", "2026-08-05", "2026-08-10", "2026-08-12", "2026-08-14"])) == "2026-08-12"
    assert signal_date_of(ov("2026-06-30", [])) == "2026-08-14"                        # no dates: quarter end + 45 days


SETS = [{"url": f"u{i}.zip", "period": p} for i, p in enumerate(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"])]


def test_historical_overviews_are_built_once_per_quarter_pair_cached_and_sorted_oldest_first(tmp_path):
    calls = []

    def build(cur, prev, period, prev_period):
        calls.append(period)
        return ov(period, ["2026-08-10"])
    out = hist_overviews(str(tmp_path), SETS, lambda s: s["url"], build)
    assert calls == ["2026-06-30", "2026-03-31", "2025-12-31"] and [o["period"] for o in out] == ["2025-12-31", "2026-03-31", "2026-06-30"]
    assert all("signal_date" in o for o in out)
    again = hist_overviews(str(tmp_path), SETS, lambda s: s["url"], build)
    assert len(calls) == 3 and [o["period"] for o in again] == [o["period"] for o in out]


def test_a_quarter_that_cannot_be_built_is_skipped_with_a_note_not_fatal(tmp_path):
    def build(cur, prev, period, prev_period):
        if period == "2026-03-31":
            raise DataUnavailable("bad zip")
        return ov(period, [])
    notes = []
    out = hist_overviews(str(tmp_path), SETS, lambda s: s["url"], build, notes=notes)
    assert [o["period"] for o in out] == ["2025-12-31", "2026-06-30"] and any("2026-03-31" in n and "bad zip" in n for n in notes)


def test_historical_insider_trades_are_loaded_per_quarter_and_cached(tmp_path):
    calls = []

    def load(path):
        calls.append(path)
        return [{"symbol": "A", "owner": "o", "side": "buy", "value": 1.0, "filed": "2026-01-02", "date": "2026-01-01", "plan": False}]
    isets = [{"quarter": "2026q1", "url": "i1"}, {"quarter": "2025q4", "url": "i0"}]
    t = hist_insiders(str(tmp_path), isets, lambda s: s["url"], load)
    assert len(t) == 2 and sorted(calls) == ["i0", "i1"]
    hist_insiders(str(tmp_path), isets, lambda s: s["url"], load)
    assert len(calls) == 2


def test_research_board_runs_end_to_end_on_planted_data_and_reports_the_evidence(tmp_path):
    overviews, closes = world(strength=1.0)

    def build_ov(cur, prev, period, prev_period):
        k = int(period[1:])
        return {**overviews[k], "period": period, "prev_period": "x", "quarter": period, "funds": []}
    sets = [{"url": f"u{i}", "period": f"q{7 - i}"} for i in range(9)]               # newest first
    # signal dates are fixed by the planted world, so override the quarter-end estimate through the funds' filing dates
    res = research_board(str(tmp_path), sets, [], lambda s: s["url"], build_ov, lambda p: [],
                         lambda t: closes.get(t), defaults={"smart": 0.3, "momentum": 0.25, "trend": 0.1, "quality": 0.15, "insider": 0.15, "politician": 0.05},
                         signal_dates={f"q{k}": DATES[SIGNAL_IDX[k]] for k in range(8)})
    assert res["signals"]["smart_money"]["verdict"] == "works" and res["n_signal_dates"] == 8
    assert res["weights"]["evidence"]["smart"] > 0 and res["meta"]["quarters"] == 8 and res["meta"]["tickers"] == N
