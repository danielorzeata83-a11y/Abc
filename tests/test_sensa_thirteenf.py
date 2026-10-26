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


from sensa.thirteenf import changes


def _p(cusip, shares, value, issuer=None):
    return {"cusip": cusip, "issuer": issuer or "ISS" + cusip, "shares": shares, "value": value}


def test_changes_lists_each_new_exited_increased_and_reduced_position():
    prev = [_p("1", 10, 100), _p("2", 10, 200), _p("3", 10, 50), _p("4", 10, 400)]
    cur = [_p("1", 25, 250),      # increased
           _p("2", 4, 80),        # reduced
           _p("3", 10, 55),       # same shares: not a change (price moved only)
           _p("9", 7, 700)]       # new ; "4" exited
    out = changes(cur, prev)
    by = {c["cusip"]: c for c in out}
    assert set(by) == {"1", "2", "4", "9"}
    assert by["9"]["type"] == "new" and by["9"]["shares_prev"] == 0 and by["9"]["shares_now"] == 7
    assert by["4"]["type"] == "exited" and by["4"]["shares_now"] == 0 and by["4"]["value_prev"] == 400
    assert by["1"]["type"] == "increased" and by["1"]["shares_now"] - by["1"]["shares_prev"] == 15
    assert by["2"]["type"] == "reduced"


def test_changes_sorted_by_size_of_the_position_involved():
    prev = [_p("1", 10, 100), _p("4", 10, 400)]
    cur = [_p("1", 20, 200), _p("9", 7, 700)]
    assert [c["cusip"] for c in changes(cur, prev)] == ["9", "4", "1"]


def test_changes_without_previous_filing_is_empty_not_all_new():
    assert changes([_p("1", 1, 1)], None) == []


def test_figi_info_returns_ticker_and_kind_for_stock_etf_and_adr():
    def post(url, payload):
        data = {"S1": {"ticker": "AAA", "exchCode": "US", "securityType": "Common Stock"},
                "E1": {"ticker": "SPY", "exchCode": "US", "securityType": "ETP"},
                "R1": {"ticker": "BABA", "exchCode": "US", "securityType": "ADR"},
                "X1": {"ticker": "ZZZ", "exchCode": "US", "securityType": "Weird Thing"}}
        return json.dumps([{"data": [data[p["idValue"]]]} for p in payload])
    info = Figi(post=post).info(["S1", "E1", "R1", "X1"])
    assert info["S1"] == {"ticker": "AAA", "kind": "stock"} and info["E1"]["kind"] == "etf"
    assert info["R1"]["kind"] == "adr" and info["X1"]["kind"] == "other"


def test_figi_throttles_between_batches_to_respect_the_free_rate_limit():
    sleeps = []
    f = Figi(post=lambda u, p: json.dumps([{"warning": "none"} for _ in p]), sleep=sleeps.append, min_interval=2.5,
             clock=lambda: 0.0)                       # frozen clock: each batch waits the full interval
    f.lookup([f"C{i:02d}" for i in range(25)])        # 3 batches
    assert sleeps == [2.5, 2.5]                        # between batches, not before the first


def test_figi_disk_cache_survives_restart_and_remembers_unknown_cusips(tmp_path):
    calls = []

    def post(url, payload):
        calls.append(len(payload))
        return json.dumps([{"data": [{"ticker": "T" + p["idValue"], "exchCode": "US", "securityType": "Common Stock"}]}
                           if p["idValue"] != "NOPE" else {"warning": "No identifier found."} for p in payload])
    path = str(tmp_path / "figi.json")
    Figi(post=post, cache_path=path).info(["A", "NOPE"])
    again = Figi(post=post, cache_path=path)
    assert again.info(["A", "NOPE"]) == {"A": {"ticker": "TA", "kind": "stock"}}
    assert calls == [2]                                # second instance answered from disk, even for NOPE


def test_figi_picks_the_shortest_us_ticker_when_a_cusip_has_several():
    def post(url, payload):
        return json.dumps([{"data": [
            {"ticker": "EXMOC", "exchCode": "US", "securityType": "Common Stock"},
            {"ticker": "XOM", "exchCode": "US", "securityType": "Common Stock"},
            {"ticker": "XON", "exchCode": "GR", "securityType": "Common Stock"}]}])
    assert Figi(post=post).lookup(["X"]) == {"X": "XOM"}


def test_figi_without_any_us_composite_prefers_a_normal_short_ticker():
    def post(url, payload):                       # shaped like the real answer for Exxon's CUSIP
        e = lambda t, x: {"ticker": t, "exchCode": x, "securityType": "Common Stock"}
        return json.dumps([{"data": [e("EXMOC", "CP"), e("EXMOC", "RC"), e("XOM", "UZ"), e("XOM", "OU"),
                                     e("1XOMM", "PO"), e("1XOMM", "L1")]}])
    assert Figi(post=post).lookup(["X"]) == {"X": "XOM"}


def test_figi_keeps_class_share_tickers_like_brk_b():
    def post(url, payload):
        return json.dumps([{"data": [{"ticker": "BRK/B", "exchCode": "US", "securityType": "Common Stock"}]}])
    assert Figi(post=post).lookup(["X"]) == {"X": "BRK/B"}


ATOM13 = """<?xml version="1.0" encoding="ISO-8859-1" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>13F-HR - E6 Portfolios, LLC (0002110817) (Filer)</title>
<link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/2110817/000211081726000006/0002110817-26-000006-index.htm"/>
<summary type="html"> &lt;b&gt;Filed:&lt;/b&gt; 2026-10-26 &lt;b&gt;AccNo:&lt;/b&gt; 0002110817-26-000006 &lt;b&gt;Size:&lt;/b&gt; 50 KB</summary></entry>
<entry><title>13F-HR/A - Old Fund LP (0000000555) (Filer)</title>
<link rel="alternate" href="https://www.sec.gov/Archives/edgar/data/555/000000055526000001/0000000555-26-000001-index.htm"/>
<summary type="html"> &lt;b&gt;Filed:&lt;/b&gt; 2026-10-24 &lt;b&gt;AccNo:&lt;/b&gt; 0000000555-26-000001 &lt;b&gt;Size:&lt;/b&gt; 5 KB</summary></entry>
<entry><title>13F-HR - E6 Portfolios, LLC (0002110817) (Filer)</title>
<link rel="alternate" href="https://www.sec.gov/Archives/edgar/data/2110817/000211081726000005/0002110817-26-000005-index.htm"/>
<summary type="html"> &lt;b&gt;Filed:&lt;/b&gt; 2026-10-20 &lt;b&gt;AccNo:&lt;/b&gt; 0002110817-26-000005 &lt;b&gt;Size:&lt;/b&gt; 40 KB</summary></entry>
<entry><title>13F-HR - Broken entry without link</title></entry>
</feed>"""

PRIMARY = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/thirteenffiler" xmlns:com="http://www.sec.gov/edgar/common">
 <headerData><submissionType>13F-HR</submissionType><filerInfo><periodOfReport>09-30-2026</periodOfReport></filerInfo></headerData>
 <formData><coverPage><reportCalendarOrQuarter>09-30-2026</reportCalendarOrQuarter>
  <filingManager><name>E6 Portfolios, LLC</name></filingManager></coverPage>
  <summaryPage><otherIncludedManagersCount>0</otherIncludedManagersCount>
   <tableEntryTotal>71</tableEntryTotal><tableValueTotal>297040000</tableValueTotal></summaryPage></formData>
</edgarSubmission>"""


def test_latest_lists_newest_filings_one_per_manager_with_cik_accession_and_date():
    class F(FakeSec):
        def __call__(self, url, headers=None):
            return ATOM13 if "browse-edgar" in url else super().__call__(url, headers)
    rows = ThirteenF("me@example.com", fetch=F()).latest(limit=10)
    assert [(r["cik"], r["accession"], r["filed"], r["form"]) for r in rows] == [
        ("0002110817", "0002110817-26-000006", "2026-10-26", "13F-HR"),
        ("0000000555", "0000000555-26-000001", "2026-10-24", "13F-HR/A")]
    assert rows[0]["name"] == "E6 Portfolios, LLC"            # the older filing of the same manager is dropped


def test_latest_respects_the_limit_and_requires_contact():
    class F(FakeSec):
        def __call__(self, url, headers=None):
            return ATOM13
    assert len(ThirteenF("me@example.com", fetch=F()).latest(limit=1)) == 1
    with pytest.raises(DataUnavailable, match="SEC_CONTACT"):
        ThirteenF("", fetch=F()).latest()


def test_cover_reads_period_holdings_count_and_value_from_primary_doc():
    class F(FakeSec):
        def __call__(self, url, headers=None):
            self.calls.append((url, headers or {}))
            if url.endswith("/primary_doc.xml"):
                return PRIMARY
            raise DataUnavailable("404")
    sec = F()
    c = ThirteenF("me@example.com", fetch=sec).cover("2110817", "0002110817-26-000006")
    assert c == {"period": "2026-09-30", "quarter": "Q3 2026", "entries": 71, "value": 297040000.0,
                 "name": "E6 Portfolios, LLC"}
    assert "/data/2110817/000211081726000006/primary_doc.xml" in sec.calls[0][0]


def test_cover_scales_old_filings_reported_in_thousands():
    class F(FakeSec):
        def __call__(self, url, headers=None):
            return PRIMARY.replace("09-30-2026", "09-30-2022")
    c = ThirteenF("me@example.com", fetch=F()).cover("1", "0000000001-22-000001", filed="2022-11-14")
    assert c["value"] == 297040000.0 * 1000


def test_figi_rate_limit_is_global_across_separate_lookup_calls():
    sleeps, now = [], [100.0]

    def sleep(s):
        sleeps.append(round(s, 3))
        now[0] += s
    f = Figi(post=lambda u, p: json.dumps([{"warning": "none"} for _ in p]), sleep=sleep,
             min_interval=2.5, clock=lambda: now[0])
    f.lookup(["A1"])                       # first request: no wait
    now[0] += 1.0                          # 1s later another page asks for a different cusip
    f.lookup(["B1"])
    now[0] += 5.0                          # long enough ago: no wait needed
    f.lookup(["C1"])
    assert sleeps == [1.5]


def test_figi_is_safe_to_call_from_several_threads():
    import threading
    posts = []

    def post(url, payload):
        posts.append([p["idValue"] for p in payload])
        return json.dumps([{"data": [{"ticker": "T", "exchCode": "US", "securityType": "Common Stock"}]} for _ in payload])
    f = Figi(post=post, sleep=lambda s: None, min_interval=0.0)
    ts = [threading.Thread(target=f.lookup, args=([f"C{i}"],)) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(x for p in posts for x in p) == sorted(f"C{i}" for i in range(8))


def test_infotable_reads_detailed_rows_with_options_and_scales_old_values():
    xml = ('<informationTable xmlns="x"><infoTable><nameOfIssuer>A</nameOfIssuer><cusip>1</cusip><value>5</value>'
           '<shrsOrPrnAmt><sshPrnamt>2</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt><putCall>Call</putCall>'
           '</infoTable></informationTable>')

    class F:
        def __call__(self, url, headers=None):
            if url.endswith("index.json"):
                return json.dumps({"directory": {"item": [{"name": "primary_doc.xml"}, {"name": "table.xml"}]}})
            return xml
    tf = ThirteenF("me@example.com", fetch=F())
    assert tf.infotable("5", "0000000005-26-000001", "2026-10-01") == [("1", "A", "CALL", 2.0, 5.0)]
    assert tf.infotable("5", "0000000005-22-000001", "2022-10-01")[0][4] == 5000.0
    assert tf.fetch("https://x/y") == xml
