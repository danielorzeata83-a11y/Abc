import pytest

from sensa.investors import SORT_KEYS, investors_page, is_prime_broker
from tests.test_sensa_holders import db  # noqa: F401  (fixture: Alpha/Beta/Gamma hold 709789101; Delta sold out)

CUSIP = "709789101"
OUT = {"shares": 1000, "as_of": "2026-06-30"}


def page(db, **kw):
    kw.setdefault("shares_out", OUT)
    return investors_page(db, CUSIP, "PEBO", **kw)


def rows(res):
    return {r["cik"]: r for r in res["data"]}


def test_summary_totals_and_counts(db):
    s = page(db)["summary"]
    # Alpha: 15 sh / 150 value, calls 700 sh / 7, puts 300 sh / 3; Beta 40 / 400; Gamma 6 / 60
    assert s["filerCount"] == 3 and s["stockShares"] == 61 and s["stockValue"] == 610
    assert (s["callValue"], s["putValue"], s["optionsValue"]) == (7, 3, 4)          # options value is net call - put, as in the original
    assert s["totalValue"] == 614 and s["filersWithOptions"] == 1 and s["callFilerCount"] == 1 and s["putFilerCount"] == 1
    assert s["contractMultiplier"] == 100 and s["soldOutCount"] == 1 and s["sharesOutstanding"] == 1000


def test_each_row_carries_value_change_and_ownership(db):
    r = rows(page(db))
    a, b, g = r["0000000001"], r["0000000002"], r["0000000003"]
    assert (a["shares"], a["stockValue"], a["optionsValue"], a["value"]) == (15, 150, 4, 154)
    assert (a["callShares"], a["putShares"], a["callContracts"], a["putContracts"]) == (700, 300, 7, 3)
    assert a["prevShares"] == 12 and a["shareChange"] == 3 and a["shareChangePct"] == 25.0 and a["changeType"] == "INCREASED"
    assert b["changeType"] == "UNCHANGED" and b["shareChange"] == 0 and b["shareChangePct"] == 0
    assert g["changeType"] == "NEW" and g["prevShares"] == 0 and g["shareChangePct"] is None and g["shareChange"] == 6
    assert a["ownershipPct"] == 1.5 and b["ownershipPct"] == 4.0


def test_a_reduced_position_is_decreased(db):
    import sqlite3
    con = sqlite3.connect(db); con.execute("UPDATE h SET shares = 30 WHERE q = 0 AND cik = '0000000002' AND kind = 'SH'"); con.commit()
    b = rows(page(db))["0000000002"]
    assert b["changeType"] == "DECREASED" and b["shareChange"] == -10 and b["shareChangePct"] == -25.0


def test_history_shows_both_quarters_and_marks_unreported(db):
    g = rows(page(db))["0000000003"]
    assert [h["label"] for h in g["history"]] == ["Q1 2026", "Q2 2026"]
    assert g["history"][0]["reported"] is False and g["history"][0]["shares"] is None
    assert g["history"][1]["reported"] is True and g["history"][1]["shares"] == 6
    assert page(db)["quarters"] == [{"label": "Q1 2026"}, {"label": "Q2 2026"}]


def test_without_a_share_count_ownership_is_none(db):
    res = page(db, shares_out=None)
    assert rows(res)["0000000001"]["ownershipPct"] is None and res["summary"]["sharesOutstanding"] is None


def test_default_sort_is_value_descending_and_pagination_slices(db):
    res = page(db, page=1, limit=2)
    assert [r["cik"] for r in res["data"]] == ["0000000002", "0000000001"]
    assert res["pagination"] == {"page": 1, "limit": 2, "total": 3, "totalPages": 2}
    assert [r["cik"] for r in page(db, page=2, limit=2)["data"]] == ["0000000003"]
    assert page(db, page=9, limit=2)["data"] == []


def test_sorting_by_other_keys_and_direction(db):
    assert [r["cik"] for r in page(db, sort_by="shares", sort_order="asc")["data"]] == ["0000000003", "0000000001", "0000000002"]
    assert [r["cik"] for r in page(db, sort_by="name", sort_order="asc")["data"]] == ["0000000001", "0000000002", "0000000003"]
    assert page(db, sort_by="shareChangePct", sort_order="desc")["data"][0]["cik"] == "0000000001"   # None (new) is always last


def test_none_values_sort_last_in_both_directions(db):
    for order in ("asc", "desc"):
        assert page(db, sort_by="shareChangePct", sort_order=order)["data"][-1]["cik"] == "0000000003"


def test_bad_sort_key_order_or_paging_is_rejected(db):
    for kw in ({"sort_by": "nope"}, {"sort_order": "sideways"}, {"page": 0}, {"limit": 0}, {"limit": 1000}):
        with pytest.raises(ValueError):
            page(db, **kw)
    assert len(SORT_KEYS) >= 15 and "value" in SORT_KEYS


def test_top_funds_and_prime_brokers_are_flagged(db):
    res = page(db, top_ciks={"0000000002"})
    assert rows(res)["0000000002"]["isTopFund"] is True and rows(res)["0000000001"]["isTopFund"] is False
    assert res["summary"]["topFundCount"] == 1
    assert is_prime_broker("GOLDMAN SACHS GROUP INC") and is_prime_broker("Morgan Stanley") and not is_prime_broker("Alpha Fund")


def test_unknown_security_gives_an_empty_page(db):
    res = investors_page(db, "999999999", "NONE", shares_out=None)
    assert res["data"] == [] and res["summary"]["filerCount"] == 0 and res["pagination"]["total"] == 0


import json as _json

from markov.data_providers import DataUnavailable
from sensa.investors import InvestorService, UnknownTicker
from sensa.thirteenf import Figi
from tests.test_sensa_tickers import FakeOpenFigi


def service(tmp_path, fetch=None):
    post = FakeOpenFigi()
    FakeOpenFigi.TICKERS["PEBO"] = "PEOPLES BANCORP INC/OH"

    def sec(url, headers=None):
        if "company_tickers" in url:
            return _json.dumps({"0": {"cik_str": 5, "ticker": "PEBO", "title": "x"}})
        return _json.dumps({"units": {"shares": [{"end": "2026-06-30", "val": 1000, "filed": "2026-08-01"}]}})
    return InvestorService(str(tmp_path), Figi(post), fetch or sec)


def test_service_resolves_the_ticker_and_adds_ownership_and_top_fund_flags(db, tmp_path):
    (tmp_path / "overview.json").write_text(_json.dumps({"funds": [{"cik": "0000000002"}]}))
    res = service(tmp_path).lookup("pebo")
    assert res["summary"]["filerCount"] == 3 and res["summary"]["topFundCount"] == 1
    assert rows(res)["0000000002"]["ownershipPct"] == 4.0 and res["summary"]["ticker"] == "PEBO"


def test_service_survives_a_failing_share_count_source(db, tmp_path):
    def down(url, headers=None):
        raise DataUnavailable("sec down")
    res = service(tmp_path, down).lookup("PEBO")
    assert res["summary"]["sharesOutstanding"] is None and res["summary"]["filerCount"] == 3


def test_service_reports_an_unmatched_ticker_and_passes_paging_through(db, tmp_path):
    s = service(tmp_path)
    with pytest.raises(UnknownTicker, match="ZZZZ"):
        s.lookup("ZZZZ")
    assert len(s.lookup("PEBO", page=1, limit=1, sort_by="shares", sort_order="asc")["data"]) == 1


def test_service_without_an_index_says_to_press_update(tmp_path):
    with pytest.raises(DataUnavailable, match="Update"):
        service(tmp_path).lookup("PEBO")
