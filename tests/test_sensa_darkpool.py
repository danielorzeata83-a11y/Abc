import json
from datetime import date

import pytest

from markov.data_providers import DataUnavailable
from sensa.darkpool import DarkPool


def row(symbol, shares, trades, week, tier="T1", kind="ATS_W_SMBL", mpid=None, name=None, notional=None):
    return {"issueSymbolIdentifier": symbol, "issueName": (symbol or "") + " Corp", "MPID": mpid, "marketParticipantName": name,
            "tierIdentifier": tier, "summaryTypeCode": kind, "weekStartDate": week, "totalWeeklyShareQuantity": float(shares),
            "totalWeeklyTradeCount": trades, "totalNotionalSum": notional}


DATA = {
    "2026-10-05": [row("AAA", 600e6, 2000, "2026-10-05"), row("BBB", 300e6, 900, "2026-10-05"), row("CCC", 100e6, 500, "2026-10-05", tier="T2"),
                   row(None, 600e6, 2000, "2026-10-05", kind="ATS_W_FIRM", mpid="UBSA", name="UBS ATS"),
                   row(None, 400e6, 1400, "2026-10-05", kind="ATS_W_FIRM", mpid="XTRA", name="Xtra ATS")],
    "2026-09-28": [row("AAA", 400e6, 1500, "2026-09-28"), row("BBB", 450e6, 1000, "2026-09-28"),
                   row(None, 850e6, 2500, "2026-09-28", kind="ATS_W_FIRM", mpid="UBSA", name="UBS ATS")],
    "2026-09-21": [row(None, 700e6, 2000, "2026-09-21", kind="ATS_W_FIRM", mpid="UBSA", name="UBS ATS"),
                   # Tier 2 is published ~2 weeks after Tier 1: totals must not mix them, or recent weeks look like a collapse
                   row(None, 600e6, 900, "2026-09-21", tier="T2", kind="ATS_W_FIRM", mpid="UBSA", name="UBS ATS")],
}
VENUES = [row("AAA", 360e6, 1000, "2026-10-05", kind="ATS_W_SMBL_FIRM", mpid="UBSA", name="UBS ATS"),
          row("AAA", 240e6, 1000, "2026-10-05", kind="ATS_W_SMBL_FIRM", mpid="XTRA", name="Xtra ATS")]


def fake_post_factory(log=None, data=None):
    data = DATA if data is None else data

    def post(url, payload, headers=None):
        if log is not None:
            log.append(payload)
        f = {c["fieldName"]: c["fieldValue"] for c in payload["compareFilters"]}
        week, kind, tier = f.get("weekStartDate"), f.get("summaryTypeCode"), f.get("tierIdentifier")
        if kind == "ATS_W_SMBL_FIRM":
            rows = [r for r in VENUES if r["issueSymbolIdentifier"] == f["issueSymbolIdentifier"] and r["weekStartDate"] == week]
        else:
            rows = [r for r in data.get(week, []) if r["summaryTypeCode"] == kind and (tier is None or r["tierIdentifier"] == tier)]
        rows = sorted(rows, key=lambda r: -r["totalWeeklyShareQuantity"])[:payload.get("limit", 100)]
        return json.dumps(rows) if rows else ""          # FINRA answers 204 with an empty body when nothing matches
    return post


def test_latest_week_probes_back_to_the_newest_week_with_data():
    log = []
    dp = DarkPool(fake_post_factory(log), today=lambda: date(2026, 10, 26))
    assert dp.latest_week() == "2026-10-05"
    weeks = []
    for p in log:
        w = next(c["fieldValue"] for c in p["compareFilters"] if c["fieldName"] == "weekStartDate")
        if w not in weeks:
            weeks.append(w)
    assert weeks[0] == "2026-10-12" and weeks[-1] == "2026-10-05"       # most recent candidate first, stops at the hit


def test_latest_week_gives_up_with_a_clear_error_when_nothing_is_published():
    dp = DarkPool(fake_post_factory(data={}), today=lambda: date(2026, 10, 26))
    with pytest.raises(DataUnavailable, match="FINRA"):
        dp.latest_week()


def test_overview_ranks_symbols_across_tiers_with_change_average_trade_and_history():
    dp = DarkPool(fake_post_factory(), today=lambda: date(2026, 10, 26))
    o = dp.overview(top=10)
    assert o["week"] == "2026-10-05" and o["prev_week"] == "2026-09-28"
    assert [r["symbol"] for r in o["top"]] == ["AAA", "BBB", "CCC"]
    a, b, c = o["top"]
    assert a["shares"] == 600e6 and a["trades"] == 2000 and a["avg_trade"] == 300000.0
    assert a["change_pct"] == 50.0 and b["change_pct"] == -33.33 and c["change_pct"] is None      # CCC had no prior week
    assert o["total_shares"] == 1000e6 and o["total_trades"] == 3400 and o["total_change_pct"] == pytest.approx(17.65, abs=0.01)
    assert [h["week"] for h in o["history"]] == ["2026-09-21", "2026-09-28", "2026-10-05"]
    assert [(v["mpid"], v["share_pct"]) for v in o["venues"]] == [("UBSA", 60.0), ("XTRA", 40.0)]


def test_symbol_view_lists_venues_with_their_share_of_the_symbols_ats_volume():
    dp = DarkPool(fake_post_factory(), today=lambda: date(2026, 10, 26))
    s = dp.symbol("aaa")
    assert s["symbol"] == "AAA" and s["week"] == "2026-10-05"
    assert [(v["mpid"], v["name"], v["share_pct"]) for v in s["venues"]] == [("UBSA", "UBS ATS", 60.0), ("XTRA", "Xtra ATS", 40.0)]
    assert dp.symbol("ZZZ")["venues"] == []


def test_results_are_cached_for_hours():
    log, t = [], [0.0]
    dp = DarkPool(fake_post_factory(log), today=lambda: date(2026, 10, 26), clock=lambda: t[0])
    dp.overview(top=5)
    n = len(log)
    t[0] = 3600.0
    dp.overview(top=5)
    assert len(log) == n
    t[0] = 7 * 3600.0
    dp.overview(top=5)
    assert len(log) > n


def test_totals_and_history_use_tier_1_only_so_weeks_stay_comparable():
    o = DarkPool(fake_post_factory(), today=lambda: date(2026, 10, 26)).overview(top=5)
    assert {h["week"]: h["shares"] for h in o["history"]}["2026-09-21"] == 700e6
    assert o["tier_note"] and "Tier 1" in o["tier_note"]
