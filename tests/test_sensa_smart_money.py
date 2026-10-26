import threading

import pytest

from markov.data_providers import DataUnavailable
from sensa.smart_money import OverviewService, format_summary
from tests.test_sensa_universe import FakeInfo, LISTING, fake_download_factory


def make(tmp_path, notify=None, listing=LISTING, download=None, log=None):
    log = [] if log is None else log
    return OverviewService(str(tmp_path), lambda: listing, download or fake_download_factory(tmp_path, log),
                           FakeInfo(), top=10, notify=notify), log


def test_overview_not_built_yet_explains_how_to_build_it(tmp_path):
    svc, _ = make(tmp_path)
    with pytest.raises(DataUnavailable, match="Update"):
        svc.overview()


def test_check_builds_once_then_is_a_no_op_until_a_newer_quarter_appears(tmp_path):
    svc, log = make(tmp_path)
    assert svc.check() is not None and svc.overview()["quarter"] == "Q2 2026"
    assert svc.check() is None and len(log) == 2


def test_start_runs_in_the_background_reports_status_and_refuses_a_second_run(tmp_path):
    gate = threading.Event()
    log = []

    def slow(url, dest):
        gate.wait(5)
        fake_download_factory(tmp_path, log)(url, dest)
    svc, _ = make(tmp_path, download=slow)
    assert svc.start() is True
    assert svc.status()["state"] == "running"
    assert svc.start() is False                          # already running
    gate.set()
    svc.wait(10)
    st = svc.status()
    assert st["state"] == "done" and st["period"] == "2026-06-30" and st["built_at"]


def test_failed_build_is_reported_not_raised_and_keeps_the_service_usable(tmp_path):
    def broken(url, dest):
        raise DataUnavailable("network down")
    svc, _ = make(tmp_path, download=broken)
    svc.start(force=True)
    svc.wait(10)
    st = svc.status()
    assert st["state"] == "error" and "network down" in st["message"]
    assert svc.start(force=True) is True                 # can retry


def test_new_quarter_triggers_exactly_one_summary_notification(tmp_path):
    sent = []
    svc, _ = make(tmp_path, notify=sent.append)
    svc.check()
    assert len(sent) == 1 and "Q2 2026" in sent[0]
    svc.check()
    assert len(sent) == 1


def test_a_broken_notifier_does_not_break_the_build(tmp_path):
    def boom(text):
        raise RuntimeError("telegram down")
    svc, _ = make(tmp_path, notify=boom)
    assert svc.check() is not None and svc.overview()["quarter"] == "Q2 2026"


def test_summary_text_is_plain_and_short_and_names_what_moved():
    o = {"quarter": "Q3 2026", "prev_quarter": "Q2 2026", "cohort": 100, "total_aum": 6e13,
         "stocks": [
             {"ticker": "AAA", "issuer": "A", "kind": "stock", "holders": 99, "holders_prev": 97, "value": 1e12,
              "active_flow": 5e10, "net_flow": 6e10, "new": 2, "exited": 0, "gone": False},
             {"ticker": "BBB", "issuer": "B", "kind": "stock", "holders": 90, "holders_prev": 95, "value": 1e11,
              "active_flow": -3e10, "net_flow": -2e10, "new": 0, "exited": 6, "gone": False},
             {"ticker": "ETF", "issuer": "E", "kind": "etf", "holders": 100, "holders_prev": 100, "value": 9e12,
              "active_flow": 9e11, "net_flow": 9e11, "new": 0, "exited": 0, "gone": False}]}
    t = format_summary(o)
    assert "Q3 2026" in t and "AAA" in t and "BBB" in t and "ETF" not in t and len(t) < 3500 and "<" not in t


def test_summary_keeps_new_listings_and_vanished_names_out_of_the_buying_and_selling_lists():
    base = {"issuer": "X", "kind": "stock", "holders": 90, "holders_prev": 90, "value": 1e11,
            "net_flow": 0.0, "new": 0, "exited": 0, "gone": False, "new_listing": False}
    o = {"quarter": "Q3 2026", "prev_quarter": "Q2 2026", "cohort": 100, "total_aum": 6e13, "stocks": [
        {**base, "ticker": "REAL", "active_flow": 1e10},
        {**base, "ticker": "SPIN", "active_flow": 9e10, "new": 80, "holders": 80, "holders_prev": 0, "new_listing": True},
        {**base, "ticker": "GONE", "active_flow": -9e10, "holders": 0, "gone": True}]}
    t = format_summary(o)
    assert "REAL" in t
    buying = t.split("Biggest active buying:")[1].split("Biggest active selling:")[0]
    selling = t.split("Biggest active selling:")[1].split("\n\n")[0]
    assert "SPIN" not in buying and "GONE" not in selling
    assert "New to the group" in t and "SPIN" in t.split("New to the group")[1]
