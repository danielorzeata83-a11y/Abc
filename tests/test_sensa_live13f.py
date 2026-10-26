from datetime import date

import pytest

from markov.data_providers import DataUnavailable
from sensa.live13f import LiveStore, LiveUpdater, next_quarter_end, parse_daily_index, parse_infotable

IDX = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Form Type   Company Name                                                  CIK
      Date Filed  File Name
---------------------------------------------------------------------------------------------------------------------------------------------
1-A/A            Upstream Life Securities Fund I, LLC                          2126686     20261023    edgar/data/2126686/0002126686-26-000007.txt
13F-HR           ABC ARBITRAGE SA                                              2049221     20261023    edgar/data/2049221/0000945621-26-001292.txt
13F-HR           AMALGAMATED BANK                                              919192      20261023    edgar/data/919192/0000919192-26-000006.txt
13F-HR/A         OLD FUND LP                                                   55          20261023    edgar/data/55/0000000055-26-000001.txt
"""


def test_daily_index_yields_13f_reports_with_padded_cik_dates_and_dashed_accession():
    rows = parse_daily_index(IDX)
    assert [(r["form"], r["cik"], r["filed"], r["accession"]) for r in rows] == [
        ("13F-HR", "0002049221", "2026-10-23", "0000945621-26-001292"),
        ("13F-HR", "0000919192", "2026-10-23", "0000919192-26-000006"),
        ("13F-HR/A", "0000000055", "2026-10-23", "0000000055-26-000001")]
    assert rows[0]["name"] == "ABC ARBITRAGE SA"


XML = """<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
<infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>1000</value>
 <shrsOrPrnAmt><sshPrnamt>10</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>50</value>
 <shrsOrPrnAmt><sshPrnamt>500</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt><putCall>Put</putCall></infoTable>
<infoTable><nameOfIssuer>A BOND</nameOfIssuer><cusip>111111111</cusip><value>9</value>
 <shrsOrPrnAmt><sshPrnamt>9</sshPrnamt><sshPrnamtType>PRN</sshPrnamtType></shrsOrPrnAmt></infoTable>
</informationTable>"""


def test_infotable_keeps_shares_and_options_and_drops_bond_principal():
    rows = parse_infotable(XML, scale=1.0)
    assert rows == [("037833100", "APPLE INC", "SH", 10.0, 1000.0), ("037833100", "APPLE INC", "PUT", 500.0, 50.0)]
    assert parse_infotable(XML, scale=1000.0)[0][4] == 1_000_000.0


def test_infotable_rejects_entities():
    with pytest.raises(DataUnavailable):
        parse_infotable('<!DOCTYPE x [<!ENTITY a "b">]><informationTable/>', 1.0)


def test_next_quarter_end():
    assert next_quarter_end("2026-06-30") == "2026-09-30"
    assert next_quarter_end("2026-12-31") == "2027-03-31"
    assert next_quarter_end("2026-03-31") == "2026-06-30"


class FakeTF:
    def __init__(self, periods=None, fail=()):
        self.urls, self.covered, self.tabled = [], [], []
        self.periods, self.fail = periods or {}, set(fail)

    def read(self, url):
        self.urls.append(url)
        if url.endswith("form.20261023.idx"):
            return IDX
        if url.endswith("form.20261026.idx"):
            return IDX.replace("13F-HR           ABC", "13F-HR           NEWCO").replace("0000945621-26-001292", "0000000009-26-000009")
        return "Form Type   Company Name   CIK  Date Filed  File Name\n"

    def cover(self, cik, accession, filed=None):
        if accession in self.fail:
            raise DataUnavailable("sec down")
        self.covered.append(accession)
        return {"period": self.periods.get(accession, "2026-09-30"), "value": 5e9, "entries": 2, "name": "x"}

    def infotable(self, cik, accession, filed=None):
        self.tabled.append(accession)
        return [("037833100", "APPLE INC", "SH", 10.0, 1000.0)]


def updater(tmp_path, tf, today=date(2026, 10, 26), bulk="2026-06-30"):
    store = LiveStore(str(tmp_path / "live.db"))
    return LiveUpdater(store, tf, lambda: bulk, today=lambda: today, sleep=lambda s: None), store


def test_new_reports_for_the_next_quarter_are_stored_and_other_periods_ignored(tmp_path):
    tf = FakeTF(periods={"0000919192-26-000006": "2026-06-30"})          # AMALGAMATED: a late report for the old quarter
    up, store = updater(tmp_path, tf)
    up.check()
    assert {f["cik"] for f in store.filers()} == {"0002049221"}           # AMALGAMATED's report is for the old quarter
    assert "0000919192-26-000006" not in tf.tabled and "0000919192-26-000006" in store.seen()
    f = {x["cik"]: x for x in store.filers()}["0002049221"]
    assert f["period"] == "2026-09-30" and f["aum"] == 5e9
    assert f["accession"] == "0000000009-26-000009"           # the same filer reported again on the 26th: the later report wins


def test_amendments_are_skipped_and_weekend_days_are_not_requested(tmp_path):
    tf = FakeTF()
    up, _ = updater(tmp_path, tf)
    up.check()
    assert "0000000055-26-000001" not in tf.covered
    assert not any(u.endswith(("form.20261024.idx", "form.20261025.idx", "form.20261003.idx")) for u in tf.urls)
    assert any(u.endswith("daily-index/2026/QTR4/form.20261001.idx") for u in tf.urls)


def test_a_second_run_fetches_only_today_and_no_known_filing_again(tmp_path):
    tf = FakeTF()
    up, _ = updater(tmp_path, tf)
    up.check()
    tf.urls.clear(); tf.covered.clear()
    up.check()
    assert len(tf.urls) == 1 and tf.urls[0].endswith("form.20261026.idx")
    assert tf.covered == []


def test_a_failing_report_is_retried_next_run_without_stopping_the_others(tmp_path):
    tf = FakeTF(fail={"0000919192-26-000006"})
    up, store = updater(tmp_path, tf)
    up.check()
    assert "0002049221" in {f["cik"] for f in store.filers()} and "0000919192-26-000006" not in store.seen()
    tf.fail.clear()
    up.check()
    assert "0000919192" in {f["cik"] for f in store.filers()}


def test_live_data_is_dropped_once_the_bulk_data_set_covers_that_quarter(tmp_path):
    tf = FakeTF()
    up, store = updater(tmp_path, tf)
    up.check()
    assert store.filers()
    store.purge_through("2026-09-30")
    assert store.filers() == []


def test_nothing_to_do_before_the_next_quarter_ends(tmp_path):
    tf = FakeTF()
    up, store = updater(tmp_path, tf, today=date(2026, 9, 15))
    up.check()
    assert tf.urls == [] and store.filers() == []


def test_holdings_are_saved_per_filer(tmp_path):
    tf = FakeTF()
    up, store = updater(tmp_path, tf)
    up.check()
    rows = store.holdings("0002049221")
    assert rows == [("037833100", "SH", 10.0, 1000.0)]


def test_status_reports_state_and_how_many_reports_are_in(tmp_path):
    up, store = updater(tmp_path, FakeTF())
    assert up.status() == {"state": "idle", "message": "", "filers": 0, "period": None}
    up.check()
    assert up.status()["filers"] == 2 and up.status()["period"] == "2026-09-30"


def test_when_every_daily_index_fails_the_run_reports_an_error_instead_of_looking_done(tmp_path):
    class Down(FakeTF):
        def read(self, url):
            raise DataUnavailable("403")
    up, _ = updater(tmp_path, Down())
    with pytest.raises(DataUnavailable, match="EDGAR"):
        up.check()


def test_requests_are_spaced_to_respect_the_sec_rate_limit(tmp_path):
    naps = []
    tf = FakeTF()
    store = LiveStore(str(tmp_path / "live.db"))
    up = LiveUpdater(store, tf, lambda: "2026-06-30", today=lambda: date(2026, 10, 26), sleep=naps.append, min_interval=0.3)
    up.check()
    assert len(naps) >= len(tf.urls) - 1 and set(naps) == {0.3}
