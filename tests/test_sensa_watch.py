import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.watch import Watcher, format_event


def fl(q, period, filed, acc, form="13F-HR"):
    return {"quarter": q, "period": period, "filed": filed, "accession": acc, "form": form}


class FakeSec:
    """Scripted filer: `filings` can grow between checks, like a real EDGAR feed."""
    def __init__(self):
        self.filings = [fl("Q1 2026", "2026-03-31", "2026-05-15", "A1")]
        self.data = {"A1": [{"issuer": "AMAZON COM INC", "cusip": "C1", "value": 400.0, "shares": 10.0},
                            {"issuer": "GONE INC", "cusip": "C4", "value": 100.0, "shares": 2.0}]}
        self.fail = set()
        self.calls = []

    def filer(self, cik):
        return {"cik": f"{int(cik):010d}", "name": "Test Capital LP", "location": "NY",
                "filings": sorted(self.filings, key=lambda f: f["period"], reverse=True)}

    def holdings(self, cik, acc, filed=None):
        self.calls.append(acc)
        if acc in self.fail:
            raise DataUnavailable("sec down")
        return self.data[acc]

    def add_q2(self):
        self.filings.append(fl("Q2 2026", "2026-06-30", "2026-08-14", "A2"))
        self.data["A2"] = [{"issuer": "AMAZON COM INC", "cusip": "C1", "value": 900.0, "shares": 25.0},   # increased
                           {"issuer": "NEWCO", "cusip": "C3", "value": 700.0, "shares": 7.0}]            # new ; C4 exited


class Figi:
    def lookup(self, cusips):
        return {"C1": "AMZN", "C3": "NEW", "C4": "GONE"}


def make(tmp_path, sec=None, notify=None):
    sec = sec or FakeSec()
    sent = [] if notify is None else notify
    w = Watcher(sec, Figi(), str(tmp_path / "watch.json"), notify=lambda text: sent.append(text),
                now=lambda: "2026-08-15T10:00:00Z")
    return w, sec, sent


def test_following_a_fund_baselines_its_history_without_alerting(tmp_path):
    w, sec, sent = make(tmp_path)
    w.follow("1609098")
    assert w.check() == [] and sent == []
    assert [f["cik"] for f in w.following()] == ["0001609098"]


def test_new_filing_creates_one_event_with_diff_and_notifies_once(tmp_path):
    w, sec, sent = make(tmp_path)
    w.follow("1609098")
    sec.add_q2()
    ev = w.check()
    assert len(ev) == 1
    e = ev[0]
    assert e["name"] == "Test Capital LP" and e["quarter"] == "Q2 2026" and e["accession"] == "A2"
    assert e["counts"] == {"new": 1, "exited": 1, "increased": 1, "reduced": 0}
    assert {(c["type"], c["ticker"]) for c in e["changes"]} == {("new", "NEW"), ("exited", "GONE"), ("increased", "AMZN")}
    assert len(sent) == 1 and "Test Capital LP" in sent[0] and "NEW" in sent[0]
    assert w.check() == [] and len(sent) == 1               # nothing new, nothing resent


def test_failed_notification_is_retried_and_event_not_duplicated(tmp_path):
    attempts = []

    def flaky(text):
        attempts.append(1)
        if len(attempts) == 1:
            raise DataUnavailable("telegram down")
    sec = FakeSec()
    w = Watcher(sec, Figi(), str(tmp_path / "w.json"), notify=flaky, now=lambda: "t")
    w.follow("1")
    sec.add_q2()
    w.check()
    assert [e["notified"] for e in w.events()] == [False]
    w.check()
    assert [e["notified"] for e in w.events()] == [True] and len(attempts) == 2


def test_filing_that_cannot_be_downloaded_is_retried_next_time(tmp_path):
    w, sec, sent = make(tmp_path)
    w.follow("1")
    sec.add_q2()
    sec.fail.add("A2")
    assert w.check() == [] and sent == []
    sec.fail.clear()
    assert len(w.check()) == 1 and len(sent) == 1


def test_amendment_is_compared_with_the_original_of_the_same_period(tmp_path):
    w, sec, sent = make(tmp_path)
    w.follow("1")
    sec.add_q2()
    w.check()
    sec.filings.append(fl("Q2 2026", "2026-06-30", "2026-08-30", "A3", form="13F-HR/A"))
    sec.data["A3"] = sec.data["A2"] + [{"issuer": "LATEADD", "cusip": "C9", "value": 50.0, "shares": 1.0}]
    ev = w.check()
    assert len(ev) == 1 and ev[0]["amended"] is True
    assert [c["cusip"] for c in ev[0]["changes"]] == ["C9"]         # only what the amendment changed


def test_unfollow_stops_checking_but_keeps_past_events(tmp_path):
    w, sec, sent = make(tmp_path)
    w.follow("1")
    sec.add_q2()
    w.check()
    w.unfollow("1")
    assert w.following() == [] and len(w.events()) == 1
    sec.filings.append(fl("Q3 2026", "2026-09-30", "2026-11-14", "A9"))
    sec.data["A9"] = []
    assert w.check() == []


def test_state_survives_a_restart_and_a_corrupt_file_is_tolerated(tmp_path):
    w, sec, sent = make(tmp_path)
    w.follow("1")
    sec.add_q2()
    w.check()
    w2, _, sent2 = make(tmp_path, sec)
    assert len(w2.events()) == 1 and w2.check() == [] and sent2 == []
    (tmp_path / "watch.json").write_text("{not json")
    w3, _, _ = make(tmp_path, sec)
    assert w3.following() == [] and w3.events() == []


def test_a_fund_that_errors_does_not_stop_the_others(tmp_path):
    sec = FakeSec()
    orig = sec.filer

    def filer(cik):
        if int(cik) == 2:
            raise DataUnavailable("no such filer")
        return orig(cik)
    sec.filer = filer
    w, _, sent = make(tmp_path, sec)
    w.follow("1")
    w.follow("2", baseline=False)        # a fund that later starts failing
    sec.add_q2()
    assert len(w.check()) == 1


def test_format_event_is_plain_text_and_within_telegram_limits():
    changes = [{"type": "new", "ticker": f"T{i}", "issuer": "X" * 40, "shares_now": 1e6, "shares_prev": 0,
                "value_now": 1e9, "value_prev": 0} for i in range(200)]
    ev = {"name": "Big Fund LP", "quarter": "Q2 2026", "form": "13F-HR", "filed": "2026-08-14", "amended": False,
          "counts": {"new": 200, "exited": 0, "increased": 0, "reduced": 0}, "changes": changes, "cik": "0000000001"}
    text = format_event(ev)
    assert len(text) <= 3900 and "Big Fund LP" in text and "<" not in text


def test_concurrent_checks_never_create_duplicate_events_or_notifications(tmp_path):
    import threading
    import time

    class SlowSec(FakeSec):
        def holdings(self, cik, acc, filed=None):
            time.sleep(0.05)                       # widen the race window
            return super().holdings(cik, acc, filed)
    sec = SlowSec()
    w, _, sent = make(tmp_path, sec)
    w.follow("1")
    sec.add_q2()
    ts = [threading.Thread(target=w.check) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(w.events()) == 1 and len(sent) == 1
