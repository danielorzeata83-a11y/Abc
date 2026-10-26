import pytest

from sensa.holders import holders_for_cusip, live_meta, sold_out_count
from sensa.investors import investors_page
from sensa.live13f import LiveStore
from tests.test_sensa_holders import db  # noqa: F401

CUSIP = "709789101"


def live_filer(cik, name, acc):
    return {"cik": cik, "name": name, "accession": acc, "filed": "2026-10-20", "form": "13F-HR", "period": "2026-09-30", "aum": 777.0}


@pytest.fixture
def live(tmp_path):
    s = LiveStore(str(tmp_path / "live.db"))
    s.add(live_filer("0000000001", "Alpha Fund", "L1"), [(CUSIP, "PEOPLES", "SH", 20.0, 200.0), (CUSIP, "PEOPLES", "CALL", 900.0, 9.0)])
    s.add(live_filer("0000000002", "Beta Capital", "L2"), [("222222222", "OTHER", "SH", 5.0, 5.0)])      # Beta sold all PEBO
    s.add(live_filer("0000000005", "Epsilon New", "L5"), [(CUSIP, "PEOPLES", "SH", 7.0, 70.0)])         # first-time filer
    return str(tmp_path / "live.db")


def by_cik(rows):
    return {r["cik"]: r for r in rows}


def test_filers_that_already_reported_use_their_new_holdings_and_the_rest_are_carried(db, live):
    r = by_cik(holders_for_cusip(db, CUSIP, live))
    assert set(r) == {"0000000001", "0000000003", "0000000005"}          # Beta left; Delta never held it now
    a, g, e = r["0000000001"], r["0000000003"], r["0000000005"]
    assert a["is_current"] is True and (a["shares"], a["stock_value"], a["prev_shares"], a["call_shares"]) == (20, 200, 15, 900)
    assert a["accession"] == "L1" and a["aum"] == 777.0
    assert g["is_current"] is False and g["shares"] == 6 and g["prev_shares"] is None
    assert e["is_current"] is True and e["prev_shares"] is None and e["filed_prev_quarter"] is False


def test_without_a_live_file_nothing_changes(db, tmp_path):
    r = by_cik(holders_for_cusip(db, CUSIP, str(tmp_path / "nope.db")))
    assert r["0000000001"]["is_current"] is False and r["0000000001"]["shares"] == 15 and "0000000002" in r


def test_sold_out_counts_carried_and_live_filers(db, live):
    assert sold_out_count(db, CUSIP, live) == 2          # Delta (carried, sold in Q2) + Beta (reported Q3 without it)
    assert sold_out_count(db, CUSIP) == 1


def test_live_meta_reports_period_and_filer_count(db, live):
    assert live_meta(live, "2026-06-30") == {"period": "2026-09-30", "filers": 3}
    assert live_meta(live, "2026-09-30") is None


def test_investors_page_marks_current_vs_carried_and_shows_three_quarters(db, live):
    res = investors_page(db, CUSIP, "PEBO", shares_out={"shares": 1000, "as_of": "x"}, live_db=live)
    assert res["quarters"] == [{"label": "Q1 2026"}, {"label": "Q2 2026"}, {"label": "Q3 2026"}]
    assert res["coverage"]["quarter"] == "Q3 2026"
    assert (res["coverage"]["currentFilers"], res["coverage"]["carriedFilers"]) == (2, 1)
    r = by_cik(res["data"])
    a = r["0000000001"]
    assert a["isCurrent"] is True and a["changeType"] == "INCREASED" and a["shareChange"] == 5 and a["ownershipPct"] == 2.0
    assert [(h["label"], h["shares"], h["reported"]) for h in a["history"]] == [("Q1 2026", 12, True), ("Q2 2026", 15, True), ("Q3 2026", 20, True)]
    g = r["0000000003"]
    assert g["isCurrent"] is False and g["history"][2]["reported"] is False and g["history"][2]["shares"] is None
    assert res["summary"]["soldOutCount"] == 2 and res["summary"]["filerCount"] == 3


def test_without_live_data_pages_keep_two_quarters(db):
    res = investors_page(db, CUSIP, "PEBO")
    assert len(res["quarters"]) == 2 and res["coverage"]["quarter"] == "Q2 2026"
