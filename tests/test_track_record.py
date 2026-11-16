import json

import pytest

from sensa.track_record import TrackRecord
from tests.test_sensa_performance import Prices


def picks(date, stocks, etfs=None, pool=None, pool_etf=None):
    return {"as_of": date,
            "stocks": [{"ticker": t, "weight": w, "price": p, "rank": i + 1} for i, (t, w, p) in enumerate(stocks)],
            "etfs": [{"ticker": t, "weight": w, "price": p, "rank": i + 1} for i, (t, w, p) in enumerate(etfs or [])],
            "pool_prices": {"stocks": pool or {t: p for t, _, p in stocks}, "etfs": pool_etf or {}}}


SERIES = {"AAA": [("2026-10-01", 10.0), ("2026-10-20", 12.0)], "BBB": [("2026-10-01", 20.0), ("2026-10-20", 18.0)],
          "CCC": [("2026-10-01", 5.0), ("2026-10-20", 5.5)], "SPY": [("2026-10-01", 100.0), ("2026-10-20", 103.0)],
          "E1": [("2026-10-01", 50.0), ("2026-10-20", 55.0)]}


def test_one_snapshot_per_date_is_kept_and_persisted(tmp_path):
    path = str(tmp_path / "h.json")
    tr = TrackRecord(path)
    tr.record(picks("2026-10-01", [("AAA", 0.6, 10.0), ("BBB", 0.4, 20.0)]))
    tr.record(picks("2026-10-01", [("AAA", 1.0, 10.0)]))                      # same day again: replaces, never duplicates
    tr.record(picks("2026-10-02", [("BBB", 1.0, 20.0)]))
    assert [s["date"] for s in TrackRecord(path).snapshots()] == ["2026-10-01", "2026-10-02"]
    assert TrackRecord(path).snapshots()[0]["stocks"] == {"AAA": {"weight": 1.0, "price": 10.0}}


def test_forward_returns_of_the_picks_the_pool_and_the_s_and_p_500():
    tr = TrackRecord(None)
    tr.record(picks("2026-10-01", [("AAA", 0.75, 10.0), ("BBB", 0.25, 20.0)], pool={"AAA": 10.0, "BBB": 20.0, "CCC": 5.0}))
    s = tr.summary(Prices(SERIES))
    row = s["rows"][0]
    assert row["date"] == "2026-10-01" and row["age_days"] == 19
    assert row["stocks"]["weighted_pct"] == pytest.approx((0.75 * 0.20 + 0.25 * -0.10) * 100)           # AAA +20%, BBB -10%
    assert row["stocks"]["equal_pct"] == pytest.approx(((0.2 - 0.1) / 2) * 100)
    assert row["stocks"]["pool_pct"] == pytest.approx(((0.2 - 0.1 + 0.1) / 3) * 100)
    assert row["spy_pct"] == pytest.approx(3.0) and row["stocks"]["excess_pct"] == pytest.approx(row["stocks"]["weighted_pct"] - 3.0)
    assert s["as_of"] == "2026-10-20"


def test_etfs_are_tracked_separately_and_missing_prices_are_left_out_not_guessed():
    tr = TrackRecord(None)
    tr.record(picks("2026-10-01", [("AAA", 0.5, 10.0), ("GONE", 0.5, 8.0)], etfs=[("E1", 1.0, 50.0)], pool_etf={"E1": 50.0}))
    row = tr.summary(Prices(SERIES))["rows"][0]
    assert row["stocks"]["weighted_pct"] == pytest.approx(20.0) and row["stocks"]["priced"] == 1 and row["stocks"]["of"] == 2
    assert row["etfs"]["weighted_pct"] == pytest.approx(10.0)


def test_aggregates_use_only_snapshots_old_enough_and_say_how_many_there_are():
    tr = TrackRecord(None)
    tr.record(picks("2026-10-01", [("AAA", 1.0, 10.0)]))
    tr.record(picks("2026-10-19", [("BBB", 1.0, 20.0)], pool={"BBB": 20.0}))
    S = {**SERIES, "BBB": [("2026-10-01", 20.0), ("2026-10-19", 20.0), ("2026-10-20", 21.0)],
         "SPY": [("2026-10-01", 100.0), ("2026-10-19", 102.0), ("2026-10-20", 103.0)]}
    s = tr.summary(Prices(S))
    assert s["snapshots"] == 2 and [r["date"] for r in s["rows"]] == ["2026-10-19", "2026-10-01"]          # newest first
    a = s["aggregate"]["stocks"]
    assert a["n"] == 2 and 0 <= a["hit_rate_pct"] <= 100 and a["avg_excess_pct"] is not None
    assert s["aggregate"]["stocks_7d"]["n"] == 1                                                       # only the 19-day-old one is 7+ days old
    assert "overlap" in s["note"].lower()


def test_empty_history_says_it_is_collecting():
    s = TrackRecord(None).summary(Prices(SERIES))
    assert s["snapshots"] == 0 and s["rows"] == [] and "collecting" in s["note"].lower()
