import pytest

from markov.data_providers import DataUnavailable
from sensa.live13f import LiveStore
from sensa.live_overview import build_live_overview
from tests.test_sensa_holders import db  # noqa: F401

CUSIP = "709789101"


class Figi:
    def info(self, cusips):
        return {c: {"ticker": "PEBO" if c == CUSIP else "OTH", "kind": "stock"} for c in cusips}


BULK = {"period": "2026-06-30", "quarter": "Q2 2026", "funds": [
    {"cik": "0000000001", "name": "Alpha Fund", "state": "NY", "aum": 9000.0},
    {"cik": "0000000002", "name": "Beta Capital", "state": "CA", "aum": 500.0}]}


def filer(cik, name, acc, aum):
    return {"cik": cik, "name": name, "accession": acc, "filed": "2026-10-20", "form": "13F-HR", "period": "2026-09-30", "aum": aum}


def test_only_top_funds_that_already_reported_are_in_the_live_view_and_compared_with_their_own_last_quarter(db, tmp_path):
    live = LiveStore(str(tmp_path / "live.db"))
    live.add(filer("0000000001", "Alpha Fund", "L1", 9500.0), [(CUSIP, "PEOPLES BANCORP INC", "SH", 20.0, 200.0),
                                                              ("333333333", "NEWCO INC", "SH", 4.0, 40.0)])
    live.add(filer("0000000099", "Outsider LP", "L9", 1.0), [(CUSIP, "PEOPLES BANCORP INC", "SH", 1.0, 10.0)])   # not in the top 100
    o = build_live_overview(BULK, db, str(tmp_path / "live.db"), Figi())
    assert o["period"] == "2026-09-30" and o["prev_period"] == "2026-06-30" and o["quarter"] == "Q3 2026"
    assert o["cohort"] == 1 and o["live"] == {"reported": 1, "of": 2}
    assert [f["name"] for f in o["funds"]] == ["Alpha Fund"] and o["funds"][0]["aum"] == 9500.0
    assert o["funds"][0]["aum_prev"] == 9000.0 and o["funds"][0]["new"] == 1 and o["funds"][0]["exited"] == 0
    s = {x["cusip"]: x for x in o["stocks"]}
    assert s[CUSIP]["ticker"] == "PEBO" and s[CUSIP]["holders"] == 1 and s[CUSIP]["holders_prev"] == 1
    assert s["333333333"]["new"] == 1


def test_no_reported_top_fund_means_nothing_to_show_yet(db, tmp_path):
    LiveStore(str(tmp_path / "live.db"))
    with pytest.raises(DataUnavailable, match="Q3 2026"):
        build_live_overview(BULK, db, str(tmp_path / "live.db"), Figi())


def test_store_keeps_issuer_names_for_share_positions(tmp_path):
    s = LiveStore(str(tmp_path / "l.db"))
    s.add(filer("0000000001", "A", "L1", 1.0), [("1", "ONE INC", "SH", 2.0, 3.0), ("1", "ONE INC", "CALL", 5.0, 1.0)])
    assert s.share_holdings(["0000000001"]) == {"0000000001": [{"cusip": "1", "issuer": "ONE INC", "value": 3.0, "shares": 2.0}]}


import json

from sensa.live_overview import load_live_overview, refresh_live_overview


def test_refresh_writes_the_live_overview_and_the_loader_serves_it_only_while_it_matches_the_complete_one(db, tmp_path):
    d = tmp_path
    (d / "overview.json").write_text(json.dumps(BULK))
    LiveStore(str(d / "live13f.db")).add(filer("0000000001", "Alpha Fund", "L1", 9500.0), [(CUSIP, "PEOPLES BANCORP INC", "SH", 20.0, 200.0)])
    assert refresh_live_overview(str(d), Figi()) is True
    assert load_live_overview(str(d))["live"] == {"reported": 1, "of": 2}
    (d / "overview.json").write_text(json.dumps({**BULK, "period": "2026-09-30"}))        # SEC published the Q3 data set
    with pytest.raises(DataUnavailable, match="Update"):
        load_live_overview(str(d))


def test_refresh_without_any_reported_fund_removes_a_stale_file_and_reports_false(db, tmp_path):
    d = tmp_path
    (d / "overview.json").write_text(json.dumps(BULK))
    (d / "overview_live.json").write_text("{}")
    LiveStore(str(d / "live13f.db"))
    assert refresh_live_overview(str(d), Figi()) is False
    assert not (d / "overview_live.json").exists()
