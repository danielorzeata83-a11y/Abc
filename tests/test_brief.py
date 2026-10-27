import json

import pytest

from sensa.brief import BriefService, build_brief


def pk(stocks, etfs=(), date="2026-10-26"):
    return {"as_of": date, "stocks": [{"ticker": t, "name": t + " Corp", "rank": i + 1, "score": 1.0} for i, t in enumerate(stocks)],
            "etfs": [{"ticker": t, "name": t + " ETF", "rank": i + 1, "score": 1.0} for i, t in enumerate(etfs)]}


def prev(stocks, etfs=(), date="2026-10-25"):
    return {"date": date, "stocks": {t: {"weight": 0.1, "price": 1.0} for t in stocks}, "etfs": {t: {"weight": 0.1, "price": 1.0} for t in etfs}}


def buys(sym, owners, value=150000.0, date="2026-10-20"):
    return [{"symbol": sym, "owner": o, "side": "buy", "value": value, "date": date, "plan": False, "role": "CEO"} for o in owners]


def section(b, sid):
    return next(s for s in b["sections"] if s["id"] == sid)


def test_picks_changes_list_who_entered_and_who_left_the_top_lists():
    b = build_brief(pk(["A", "B", "C"], ["E1"]), prev(["A", "X", "Y"], ["E0"]), [], [], [])
    items = section(b, "picks")["items"]
    text = " | ".join(i["text"] for i in items)
    assert "B" in text and "C" in text and "entered" in text.lower() and "X" in text and "left" in text.lower() and "E1" in text and "E0" in text
    assert {i["key"] for i in items} >= {"picks:in:stock:B", "picks:out:stock:X", "picks:in:etf:E1"}


def test_first_ever_snapshot_has_no_change_section_noise():
    b = build_brief(pk(["A"]), None, [], [], [])
    assert section(b, "picks")["items"] == []


def test_insider_cluster_buys_need_three_buyers_and_real_money():
    trades = buys("CLU", ["a", "b", "c"]) + buys("TWO", ["a", "b"]) + buys("TINY", ["a", "b", "c"], value=2000.0)
    items = section(build_brief(pk([]), None, trades, [], []), "insiders")["items"]
    assert [i["ticker"] for i in items] == ["CLU"] and "3 insiders" in items[0]["text"] and "$450k" in items[0]["text"]


def test_house_purchases_by_two_or_more_members_are_flagged():
    pols = [{"ticker": "NVDA", "type": "purchase", "member": "m1", "date": "2026-10-20"}, {"ticker": "NVDA", "type": "purchase", "member": "m2", "date": "2026-10-21"},
            {"ticker": "ONE", "type": "purchase", "member": "m1", "date": "2026-10-21"}, {"ticker": "NVDA", "type": "sale", "member": "m3", "date": "2026-10-21"}]
    items = section(build_brief(pk([]), None, [], pols, []), "politicians")["items"]
    assert [i["ticker"] for i in items] == ["NVDA"] and "2 House members bought" in items[0]["text"]


def test_followed_fund_filings_and_extra_items_are_included():
    ev = [{"id": "e1", "name": "Alpha Fund", "quarter": "Q3 2026", "counts": {"new": 3, "exited": 1, "increased": 2, "reduced": 0}, "cik": "0000000001"}]
    extra = [{"section": "portfolio", "title": "Your portfolio", "items": [{"key": "pf:x", "text": "NVDA is 40% of your portfolio", "ticker": "NVDA", "severity": "warn"}]}]
    b = build_brief(pk([]), None, [], [], ev, extra=extra)
    assert "Alpha Fund" in section(b, "funds")["items"][0]["text"] and "3 new" in section(b, "funds")["items"][0]["text"]
    assert section(b, "portfolio")["items"][0]["severity"] == "warn"


def test_service_marks_new_items_keeps_history_and_sends_each_alert_only_once(tmp_path):
    path = str(tmp_path / "brief.json")
    sent = []
    svc = BriefService(path)
    b1 = build_brief(pk(["A", "B"]), prev(["A", "X"]), [], [], [])
    out1 = svc.store(b1)
    assert out1["new_count"] >= 2
    svc.notify(out1, sent.append)
    assert len(sent) == 1 and "B" in sent[0]
    b2 = build_brief(pk(["A", "B"]), prev(["A", "X"]), [], [], [])               # nothing changed since
    out2 = svc.store(b2)
    assert out2["new_count"] == 0
    svc.notify(out2, sent.append)
    assert len(sent) == 1                                                        # no duplicate message
    b3 = build_brief(pk(["A", "C"]), prev(["A", "B"]), [], [], [])
    assert svc.store(b3)["new_count"] >= 1
    assert len(BriefService(path).history()) == 3 and BriefService(path).latest()["date"] == b3["date"]


def test_a_failing_notifier_never_breaks_the_job(tmp_path):
    svc = BriefService(str(tmp_path / "b.json"))
    out = svc.store(build_brief(pk(["A"]), prev(["X"]), [], [], []))

    def boom(text):
        raise OSError("telegram down")
    svc.notify(out, boom)                                                        # must not raise
