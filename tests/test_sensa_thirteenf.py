from sensa.thirteenf import activity, aggregate, quarter_label, summarize


def test_quarter_label_from_report_period():
    assert quarter_label("2026-06-30") == "Q2 2026"
    assert quarter_label("2025-12-31") == "Q4 2025"
    assert quarter_label("2026-03-31") == "Q1 2026"


def test_aggregate_merges_lines_with_the_same_cusip():
    rows = [{"issuer": "ACME", "cusip": "111", "value": 100.0, "shares": 10.0},
            {"issuer": "ACME", "cusip": "111", "value": 50.0, "shares": 5.0},      # e.g. a second manager line
            {"issuer": "BETA", "cusip": "222", "value": 25.0, "shares": 1.0}]
    out = aggregate(rows)
    assert out == [{"issuer": "ACME", "cusip": "111", "value": 150.0, "shares": 15.0},
                   {"issuer": "BETA", "cusip": "222", "value": 25.0, "shares": 1.0}]


def test_summarize_total_count_and_weights_sorted_by_value():
    s = summarize([{"issuer": "B", "cusip": "2", "value": 25.0, "shares": 1.0},
                   {"issuer": "A", "cusip": "1", "value": 75.0, "shares": 3.0}])
    assert s["total"] == 100.0 and s["count"] == 2
    assert [h["cusip"] for h in s["holdings"]] == ["1", "2"]
    assert s["holdings"][0]["weight"] == 75.0


def test_summarize_empty_portfolio():
    assert summarize([]) == {"total": 0.0, "count": 0, "holdings": []}


def test_activity_classifies_new_increased_reduced_exited_by_share_change():
    prev = [{"cusip": "1", "shares": 10.0}, {"cusip": "2", "shares": 10.0},
            {"cusip": "3", "shares": 10.0}, {"cusip": "4", "shares": 10.0}]
    cur = [{"cusip": "1", "shares": 20.0},    # increased
           {"cusip": "2", "shares": 5.0},     # reduced
           {"cusip": "3", "shares": 10.0},    # unchanged
           {"cusip": "9", "shares": 7.0}]     # new ; "4" exited
    a = activity(cur, prev)
    assert a == {"new": 1, "increased": 1, "reduced": 1, "exited": 1}


def test_activity_without_a_previous_quarter_counts_everything_as_new():
    assert activity([{"cusip": "1", "shares": 1.0}], None)["new"] == 1


import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.thirteenf import Figi, ThirteenF

SUBMISSIONS = {"name": "Darsana Capital Partners LP",
               "addresses": {"business": {"city": "NEW YORK", "stateOrCountry": "NY"}},
               "filings": {"recent": {
                   "form": ["13F-HR", "8-K", "13F-HR", "13F-HR/A"],
                   "reportDate": ["2026-06-30", "2026-07-01", "2026-03-31", "2025-12-31"],
                   "filingDate": ["2026-08-14", "2026-07-02", "2026-05-15", "2026-02-20"],
                   "accessionNumber": ["0001172661-26-003746", "x", "0001172661-26-002303",
                                       "0001172661-26-000999"]}}}

INFOTABLE = """<?xml version="1.0"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
 <infoTable><nameOfIssuer>AMAZON COM INC</nameOfIssuer><cusip>023135106</cusip><value>600</value>
  <shrsOrPrnAmt><sshPrnamt>10</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
 <infoTable><nameOfIssuer>AMAZON COM INC</nameOfIssuer><cusip>023135106</cusip><value>400</value>
  <shrsOrPrnAmt><sshPrnamt>5</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
</informationTable>"""


class FakeSec:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers=None):
        self.calls.append((url, headers or {}))
        if "submissions/CIK0001609098.json" in url:
            return json.dumps(SUBMISSIONS)
        if url.endswith("/index.json"):
            return json.dumps({"directory": {"item": [{"name": "primary_doc.xml"},
                                                       {"name": "form13fInfoTable.xml"}]}})
        if url.endswith("form13fInfoTable.xml"):
            return INFOTABLE
        raise DataUnavailable("404 " + url)


def test_filer_lists_only_13f_holdings_reports_newest_first_with_quarters():
    f = ThirteenF("me@example.com", fetch=FakeSec()).filer("1609098")
    assert f["name"] == "Darsana Capital Partners LP" and f["location"] == "New York, NY"
    assert f["cik"] == "0001609098"
    assert [x["quarter"] for x in f["filings"]] == ["Q2 2026", "Q1 2026", "Q4 2025"]
    assert f["filings"][0] == {"quarter": "Q2 2026", "period": "2026-06-30", "filed": "2026-08-14",
                               "accession": "0001172661-26-003746", "form": "13F-HR"}
    assert f["filings"][2]["form"] == "13F-HR/A"


def test_holdings_reads_the_info_table_skipping_primary_doc_and_merges_lines():
    sec = FakeSec()
    rows = ThirteenF("me@example.com", fetch=sec).holdings("1609098", "0001172661-26-003746")
    assert rows == [{"issuer": "AMAZON COM INC", "cusip": "023135106", "value": 1000.0, "shares": 15.0}]
    assert any("/data/1609098/000117266126003746/" in u for u, _ in sec.calls)


def test_13f_requires_contact_and_declares_it_in_user_agent():
    with pytest.raises(DataUnavailable, match="SEC_CONTACT"):
        ThirteenF("", fetch=FakeSec()).filer("1609098")
    sec = FakeSec()
    ThirteenF("me@example.com", fetch=sec).filer("1609098")
    assert "me@example.com" in sec.calls[0][1]["User-Agent"]


def test_13f_rejects_xml_with_entities():
    class Evil(FakeSec):
        def __call__(self, url, headers=None):
            return '<!DOCTYPE x [<!ENTITY a "b">]><informationTable/>' if url.endswith(".xml") and "primary" not in url \
                else super().__call__(url, headers)
    with pytest.raises(DataUnavailable):
        ThirteenF("me@example.com", fetch=Evil()).holdings("1609098", "0001172661-26-003746")


def test_figi_maps_cusips_in_batches_of_ten_and_caches():
    posts = []

    def post(url, payload):
        posts.append([p["idValue"] for p in payload])
        return json.dumps([{"data": [{"ticker": "T" + p["idValue"]}]} if p["idValue"] != "BAD" else {"warning": "No identifier found."}
                           for p in payload])
    f = Figi(post=post)
    cusips = [f"C{i:02d}" for i in range(12)] + ["BAD"]
    m = f.lookup(cusips)
    assert m["C03"] == "TC03" and "BAD" not in m
    assert [len(p) for p in posts] == [10, 3]
    f.lookup(["C01"])
    assert len(posts) == 2          # cached


def test_values_before_2023_are_reported_in_thousands_and_scaled_to_dollars():
    tf = ThirteenF("me@example.com", fetch=FakeSec())
    old = tf.holdings("1609098", "0001172661-26-003746", filed="2022-11-14")
    new = tf.holdings("1609098", "0001172661-26-003746", filed="2023-02-14")
    assert old[0]["value"] == 1_000_000.0 and new[0]["value"] == 1000.0     # 1000 in the fixture
    assert tf.holdings("1609098", "0001172661-26-003746")[0]["value"] == 1000.0   # unknown date: as filed


def test_figi_prefers_the_us_listed_common_stock_over_other_listings():
    def post(url, payload):
        return json.dumps([{"data": [
            {"ticker": "TPD", "exchCode": "GR", "securityType": "Common Stock"},
            {"ticker": "SGI", "exchCode": "US", "securityType": "Common Stock"},
            {"ticker": "SGIX", "exchCode": "US", "securityType": "Depositary Receipt"}]}])
    assert Figi(post=post).lookup(["X"]) == {"X": "SGI"}


def test_figi_falls_back_to_first_result_when_no_us_listing_exists():
    def post(url, payload):
        return json.dumps([{"data": [{"ticker": "ABC", "exchCode": "LN", "securityType": "Common Stock"}]}])
    assert Figi(post=post).lookup(["X"]) == {"X": "ABC"}
