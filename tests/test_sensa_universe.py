import io

import pytest

from sensa.universe import load_holdings, read_tsv, select_managers


def tsv(header, *rows):
    return io.StringIO("\t".join(header) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n")


SUB_H = ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"]
COV_H = ["ACCESSION_NUMBER", "ISAMENDMENT", "AMENDMENTTYPE", "FILINGMANAGER_NAME",
         "FILINGMANAGER_STATEORCOUNTRY", "REPORTTYPE"]
SUM_H = ["ACCESSION_NUMBER", "TABLEENTRYTOTAL", "TABLEVALUETOTAL"]


def fixture():
    sub = tsv(SUB_H,
              ["A1", "14-AUG-2026", "13F-HR", "0000000001", "30-JUN-2026"],      # big fund
              ["A2", "14-AUG-2026", "13F-HR", "0000000002", "30-JUN-2026"],      # mid fund
              ["A2R", "20-AUG-2026", "13F-HR/A", "0000000002", "30-JUN-2026"],   # its restatement
              ["A3", "14-AUG-2026", "13F-HR", "0000000003", "30-JUN-2026"],      # small fund
              ["A3N", "21-AUG-2026", "13F-HR/A", "0000000003", "30-JUN-2026"],   # extra holdings only
              ["A4", "14-AUG-2026", "13F-NT", "0000000004", "30-JUN-2026"],      # notice: no holdings
              ["A5", "14-AUG-2026", "13F-HR", "0000000005", "31-MAR-2026"])      # another quarter
    cov = tsv(COV_H,
              ["A1", "", "", "Big Fund LP", "NY", "13F HOLDINGS REPORT"],
              ["A2", "", "", "Mid Fund", "CA", "13F HOLDINGS REPORT"],
              ["A2R", "Y", "RESTATEMENT", "Mid Fund", "CA", "13F HOLDINGS REPORT"],
              ["A3", "", "", "Small Fund", "TX", "13F HOLDINGS REPORT"],
              ["A3N", "Y", "NEW HOLDINGS", "Small Fund", "TX", "13F HOLDINGS REPORT"],
              ["A4", "", "", "Notice Only", "FL", "13F NOTICE"],
              ["A5", "", "", "Old Quarter", "WA", "13F HOLDINGS REPORT"])
    summ = tsv(SUM_H, ["A1", "10", "9000"], ["A2", "5", "500"], ["A2R", "6", "700"],
               ["A3", "2", "100"], ["A3N", "1", "10"], ["A4", "0", "0"], ["A5", "1", "99999"])
    return sub, cov, summ


def test_read_tsv_yields_dicts_and_tolerates_quotes_inside_names():
    rows = list(read_tsv(io.StringIO('A\tB\n1\t"quoted" name\n')))
    assert rows == [{"A": "1", "B": '"quoted" name'}]


def test_select_managers_ranks_by_value_for_the_period_only_and_uses_restatements():
    sub, cov, summ = fixture()
    ms = select_managers(sub, cov, summ, "2026-06-30")
    assert [m["cik"] for m in ms] == ["0000000001", "0000000002", "0000000003"]
    assert ms[1]["accession"] == "A2R" and ms[1]["aum"] == 700.0 and ms[1]["form"] == "13F-HR/A"
    assert ms[2]["accession"] == "A3"                       # NEW HOLDINGS amendment does not replace the original
    assert ms[0] == {"cik": "0000000001", "name": "Big Fund LP", "state": "NY", "accession": "A1",
                     "filed": "2026-08-14", "form": "13F-HR", "aum": 9000.0, "entries": 10}


def test_select_managers_limits_to_top_n():
    sub, cov, summ = fixture()
    assert [m["cik"] for m in select_managers(sub, cov, summ, "2026-06-30", top=2)] == ["0000000001", "0000000002"]


def test_load_holdings_keeps_only_requested_filings_and_plain_shares_and_merges_cusips():
    H = ["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL"]
    inf = tsv(H,
              ["A1", "APPLE INC", "037833100", "100", "10", "SH", ""],
              ["A1", "APPLE INC", "037833100", "50", "5", "SH", ""],        # second line, same cusip
              ["A1", "APPLE INC", "037833100", "999", "99", "SH", "Call"],  # option: not a share holding
              ["A1", "SOME BOND", "111111111", "70", "70", "PRN", ""],      # bond principal: excluded
              ["A2R", "TESLA INC", "88160R101", "30", "3", "SH", ""],
              ["ZZZ", "OTHER", "222222222", "1", "1", "SH", ""],            # not selected
              ["A1", "BAD ROW", "333333333", "x", "1", "SH", ""])           # unparsable value: skipped
    out = load_holdings(inf, {"A1": "0000000001", "A2R": "0000000002"})
    assert out["0000000001"] == [{"cusip": "037833100", "issuer": "APPLE INC", "value": 150.0, "shares": 15.0}]
    assert out["0000000002"][0]["cusip"] == "88160R101"
    assert "ZZZ" not in out


from sensa.universe import aggregate_stocks


def h(cusip, shares, value, issuer=None):
    return {"cusip": cusip, "issuer": issuer or "ISS" + cusip, "shares": float(shares), "value": float(value)}


CUR = {"F1": [h("A", 10, 100), h("B", 5, 50)],
       "F2": [h("A", 20, 200)],
       "F3": [h("C", 1, 10)]}                          # F3 has no previous filing
PREV = {"F1": [h("A", 10, 90), h("D", 7, 70)],
        "F2": [h("A", 10, 100), h("B", 3, 30)]}


def stock(rows, cusip):
    return next(r for r in rows if r["cusip"] == cusip)


def test_most_held_stock_counts_funds_value_and_average_portfolio_weight():
    rows = aggregate_stocks(CUR, PREV)
    a = stock(rows, "A")
    assert a["holders"] == 2 and a["holders_prev"] == 2
    assert a["value"] == 300.0 and a["shares"] == 30.0
    assert a["avg_weight"] == pytest.approx((100 / 150 * 100 + 100.0) / 2)
    assert rows[0]["cusip"] == "A"                     # sorted: most holders first


def test_flows_and_changes_cover_added_reduced_new_and_exited_funds():
    rows = aggregate_stocks(CUR, PREV)
    a, b, d = stock(rows, "A"), stock(rows, "B"), stock(rows, "D")
    assert (a["added"], a["reduced"], a["new"], a["exited"]) == (1, 0, 0, 0)
    assert a["net_shares"] == 10.0 and a["net_flow"] == pytest.approx(100.0)       # price ref 300/30 = 10
    assert (b["new"], b["exited"]) == (1, 1) and b["holders"] == 1 and b["holders_prev"] == 1
    assert b["net_shares"] == 2.0 and b["net_flow"] == pytest.approx(20.0)
    assert d["holders"] == 0 and d["holders_prev"] == 1 and d["exited"] == 1
    assert d["net_shares"] == -7.0 and d["net_flow"] == pytest.approx(-70.0)       # priced at last quarter


def test_fund_without_previous_filing_counts_as_holder_but_not_in_flows():
    c = stock(aggregate_stocks(CUR, PREV), "C")
    assert c["holders"] == 1 and c["holders_prev"] == 0
    assert (c["new"], c["exited"], c["added"], c["reduced"], c["net_shares"]) == (0, 0, 0, 0, 0.0)


def test_aggregate_without_a_previous_quarter_has_no_flows():
    rows = aggregate_stocks(CUR, {})
    assert all(r["net_shares"] == 0 and r["new"] == 0 for r in rows)
    assert stock(rows, "A")["holders"] == 2


from sensa.universe import rank_funds


def mgr(cik, name, aum):
    return {"cik": cik, "name": name, "state": "NY", "accession": "a" + cik, "filed": "2026-08-14",
            "form": "13F-HR", "aum": float(aum), "entries": 2}


def test_rank_funds_reports_change_concentration_turnover_and_top_positions():
    managers = [mgr("F1", "Fund One", 1000), mgr("F2", "Fund Two", 500), mgr("F3", "Fund Three", 100)]
    prev_managers = {"F1": mgr("F1", "Fund One", 800), "F2": mgr("F2", "Fund Two", 600)}
    cur = {"F1": [h("A", 10, 600), h("B", 5, 400)], "F2": [h("A", 20, 500)], "F3": [h("C", 1, 100)]}
    prev = {"F1": [h("A", 10, 500), h("D", 7, 300)], "F2": [h("A", 20, 600)]}
    rows = rank_funds(managers, cur, prev_managers, prev)
    f1, f2, f3 = rows
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert f1["aum_prev"] == 800.0 and f1["aum_change_pct"] == 25.0
    assert f2["aum_change_pct"] == pytest.approx(-16.67, abs=0.01)
    assert f3["aum_prev"] is None and f3["aum_change_pct"] is None
    assert [t["cusip"] for t in f1["top"]] == ["A", "B"] and f1["top"][0]["weight"] == 60.0
    assert f1["top10_pct"] == 100.0 and f1["positions"] == 2
    # F1 (weights at end-of-quarter prices): before A .667 / D .333, after A .6 / B .4 -> 0.5 * sum|dw| = 40%
    assert (f1["new"], f1["exited"]) == (1, 1) and f1["turnover_pct"] == pytest.approx(40.0, abs=0.01)
    assert f2["turnover_pct"] == 0.0 and f3["turnover_pct"] is None


def test_rank_funds_handles_a_manager_with_no_share_holdings():
    rows = rank_funds([mgr("F9", "Options Only LP", 50)], {}, {}, {})
    assert rows[0]["positions"] == 0 and rows[0]["top"] == [] and rows[0]["top10_pct"] == 0.0


import zipfile

from markov.data_providers import DataUnavailable
from sensa.universe import build_overview, quarter_end_in_window, find_data_sets


def make_zip(path, period_iso, funds):
    """funds: {cik: (accession, name, aum, [(name, cusip, value, shares)])}"""
    mon = {"03": "MAR", "06": "JUN", "09": "SEP", "12": "DEC"}[period_iso[5:7]]
    per = f"{period_iso[8:]}-{mon}-{period_iso[:4]}"
    sub, cov, summ, inf = ([] for _ in range(4))
    for cik, (acc, name, aum, rows) in funds.items():
        sub.append([acc, "14-AUG-2026", "13F-HR", cik, per])
        cov.append([acc, "", "", name, "NY", "13F HOLDINGS REPORT"])
        summ.append([acc, str(len(rows)), str(aum)])
        inf += [[acc, n, c, str(v), str(s), "SH", ""] for n, c, v, s in rows]
    t = lambda head, rows: "\t".join(head) + "\n" + "".join("\t".join(r) + "\n" for r in rows)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("SUBMISSION.tsv", t(SUB_H, sub))
        z.writestr("COVERPAGE.tsv", t(COV_H, cov))
        z.writestr("SUMMARYPAGE.tsv", t(SUM_H, summ))
        z.writestr("INFOTABLE.tsv", t(["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE", "SSHPRNAMT",
                                       "SSHPRNAMTTYPE", "PUTCALL"], inf))


class FakeInfo:
    def info(self, cusips):
        m = {"A": {"ticker": "AAA", "kind": "stock"}, "E": {"ticker": "ETFX", "kind": "etf"}}
        return {c: m[c] for c in cusips if c in m}


def test_build_overview_end_to_end_from_two_quarterly_archives(tmp_path):
    cur, prev = str(tmp_path / "q2.zip"), str(tmp_path / "q1.zip")
    make_zip(cur, "2026-06-30", {
        "0000000001": ("A1", "Big Fund", 1000, [("ALPHA", "A", 600, 60), ("ETF X", "E", 400, 40)]),
        "0000000002": ("A2", "Mid Fund", 500, [("ALPHA", "A", 500, 50)]),
        "0000000003": ("A3", "Tiny Fund", 10, [("ALPHA", "A", 10, 1)])})
    make_zip(prev, "2026-03-31", {
        "0000000001": ("B1", "Big Fund", 800, [("ALPHA", "A", 300, 30)]),
        "0000000002": ("B2", "Mid Fund", 600, [("ALPHA", "A", 600, 60)])})
    o = build_overview(cur, prev, "2026-06-30", "2026-03-31", top=2, figi=FakeInfo())
    assert o["period"] == "2026-06-30" and o["quarter"] == "Q2 2026" and o["prev_quarter"] == "Q1 2026"
    assert [f["name"] for f in o["funds"]] == ["Big Fund", "Mid Fund"]            # Tiny Fund is outside the top 2
    assert o["cohort"] == 2 and o["comparable"] == 2 and o["total_aum"] == 1500.0
    alpha = next(s for s in o["stocks"] if s["cusip"] == "A")
    assert alpha["ticker"] == "AAA" and alpha["kind"] == "stock" and alpha["holders"] == 2
    assert alpha["net_shares"] == 20.0                   # Big +30, Mid -10
    etf = next(s for s in o["stocks"] if s["cusip"] == "E")
    assert etf["kind"] == "etf" and etf["new"] == 1


def test_build_overview_fails_clearly_when_the_period_has_no_reports(tmp_path):
    z = str(tmp_path / "q.zip")
    make_zip(z, "2026-03-31", {"0000000001": ("A1", "F", 10, [("ALPHA", "A", 10, 1)])})
    with pytest.raises(DataUnavailable, match="2026-06-30"):
        build_overview(z, z, "2026-06-30", "2026-03-31", top=5, figi=FakeInfo())


def test_build_overview_refuses_oversized_archive_members(tmp_path):
    cur = str(tmp_path / "q.zip")
    make_zip(cur, "2026-06-30", {"0000000001": ("A1", "F", 10, [("ALPHA", "A", 10, 1)])})
    with pytest.raises(DataUnavailable, match="too large"):
        build_overview(cur, cur, "2026-06-30", "2026-06-30", top=5, figi=FakeInfo(), max_member_bytes=10)


def test_quarter_end_inside_a_data_set_window():
    assert quarter_end_in_window("01jun2026-31aug2026") == "2026-06-30"
    assert quarter_end_in_window("01mar2026-31may2026") == "2026-03-31"
    assert quarter_end_in_window("01dec2025-28feb2026") == "2025-12-31"
    assert quarter_end_in_window("01sep2025-30nov2025") == "2025-09-30"


def test_find_data_sets_lists_zip_urls_newest_first_with_their_period():
    html = ('<a href="/files/structureddata/data/form-13f-data-sets/01mar2026-31may2026_form13f.zip">x</a>'
            '<a href="/files/datastandardsinnovation/data/form-13f-data-sets/01jun2026-31aug2026_form13f.zip">y</a>'
            '<a href="/files/structureddata/data/form-13f-data-sets/2023q4_form13f.zip">old</a>')
    sets = find_data_sets(html)
    assert [s["period"] for s in sets] == ["2026-06-30", "2026-03-31"]          # 2023q4 naming is ignored
    assert sets[0]["url"] == "https://www.sec.gov/files/datastandardsinnovation/data/form-13f-data-sets/01jun2026-31aug2026_form13f.zip"


import json as _json

from sensa.universe import load_overview, refresh_overview

LISTING = ('<a href="/files/datastandardsinnovation/data/form-13f-data-sets/01jun2026-31aug2026_form13f.zip">q2</a>'
           '<a href="/files/structureddata/data/form-13f-data-sets/01mar2026-31may2026_form13f.zip">q1</a>')


def fake_download_factory(tmp_path, log):
    def download(url, dest):
        log.append(url)
        if "01jun2026" in url:
            make_zip(dest, "2026-06-30", {"0000000001": ("A1", "Big Fund", 1000, [("ALPHA", "A", 600, 60)])})
        else:
            make_zip(dest, "2026-03-31", {"0000000001": ("B1", "Big Fund", 800, [("ALPHA", "A", 300, 30)])})
    return download


def test_refresh_downloads_two_newest_sets_builds_and_stores_the_overview(tmp_path):
    log = []
    o = refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10)
    assert o["quarter"] == "Q2 2026" and len(log) == 2
    stored = load_overview(str(tmp_path))
    assert stored["funds"][0]["name"] == "Big Fund" and stored["stocks"][0]["ticker"] == "AAA"


def test_refresh_is_a_no_op_when_the_latest_quarter_is_already_built(tmp_path):
    log = []
    refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10)
    assert refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10) is None
    assert len(log) == 2                                  # nothing downloaded again
    assert refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10, force=True)


def test_refresh_reuses_already_downloaded_archives(tmp_path):
    log = []
    refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10)
    refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10, force=True)
    assert len(log) == 2


def test_refresh_needs_two_consecutive_quarters():
    with pytest.raises(DataUnavailable, match="two"):
        refresh_overview("/tmp/x", LISTING.split("<a")[1].join(["<a", ""]), lambda u, d: None, FakeInfo())


def test_load_overview_without_a_build_explains_what_to_run(tmp_path):
    with pytest.raises(DataUnavailable, match="smart_money_build"):
        load_overview(str(tmp_path))


def test_a_failed_build_never_replaces_a_good_stored_overview(tmp_path):
    log = []
    refresh_overview(str(tmp_path), LISTING, fake_download_factory(tmp_path, log), FakeInfo(), top=10)

    def broken(url, dest):
        raise DataUnavailable("network down")
    for p in (tmp_path / "zips").glob("*.zip"):
        p.unlink()
    with pytest.raises(DataUnavailable):
        refresh_overview(str(tmp_path), LISTING, broken, FakeInfo(), top=10, force=True)
    assert load_overview(str(tmp_path))["quarter"] == "Q2 2026"


def test_find_data_sets_skips_windows_without_a_quarter_end():
    html = ('<a href="/files/structureddata/data/form-13f-data-sets/01jan2024-29feb2024_form13f.zip">x</a>'
            '<a href="/files/structureddata/data/form-13f-data-sets/01mar2024-31may2024_form13f.zip">y</a>')
    assert [s["period"] for s in find_data_sets(html)] == ["2024-03-31"]


from sensa.universe import adjust_previous, split_factors


def many_funds(ratio_by_fund):
    cur = {f"F{i}": [h("X", 100 * r, 1000 * r)] for i, r in enumerate(ratio_by_fund)}
    prev = {f"F{i}": [h("X", 100, 500)] for i in range(len(ratio_by_fund))}
    return cur, prev


def test_split_detected_when_nearly_every_fund_shows_the_same_share_ratio():
    cur, prev = many_funds([4.0, 4.0, 4.02, 3.98, 4.0, 4.0, 4.01, 9.0])      # 7 of 8 agree on 4x
    assert split_factors(cur, prev)["X"] == pytest.approx(4.0, abs=0.05)


def test_no_split_for_mixed_ratios_few_funds_or_small_drift():
    cur, prev = many_funds([1.0, 2.0, 0.5, 3.0, 1.2, 0.9])
    assert split_factors(cur, prev) == {}
    cur, prev = many_funds([4.0, 4.0, 4.0])                                   # too few funds to call it a split
    assert split_factors(cur, prev) == {}
    cur, prev = many_funds([1.1] * 8)                                         # uniform +10% is inflow, not a split
    assert split_factors(cur, prev) == {}


def test_reverse_split_is_detected_too():
    cur, prev = many_funds([0.1] * 8)
    assert split_factors(cur, prev)["X"] == pytest.approx(0.1, abs=0.005)


def test_adjust_previous_rescales_only_the_split_stocks_shares_not_values():
    prev = {"F1": [h("X", 100, 500), h("Y", 7, 70)]}
    out = adjust_previous(prev, {"X": 4.0})
    assert out["F1"][0] == {"cusip": "X", "issuer": "ISSX", "shares": 400.0, "value": 500.0}
    assert out["F1"][1]["shares"] == 7.0 and prev["F1"][0]["shares"] == 100.0       # input untouched


def test_a_split_no_longer_shows_up_as_everybody_buying():
    cur, prev = many_funds([4.0] * 8)
    rows = aggregate_stocks(cur, adjust_previous(prev, split_factors(cur, prev)))
    x = stock(rows, "X")
    assert x["added"] == 0 and x["reduced"] == 0 and x["net_shares"] == pytest.approx(0.0, abs=1e-6)


def test_active_flow_removes_a_funds_uniform_scaling_but_raw_flow_keeps_it():
    cur = {"F1": [h("A", 110, 1100), h("B", 55, 550)]}                       # everything +10%: pure inflow
    prev = {"F1": [h("A", 100, 1000), h("B", 50, 500)]}
    a = stock(aggregate_stocks(cur, prev), "A")
    assert a["net_shares"] == pytest.approx(10.0) and a["net_flow"] == pytest.approx(100.0)
    assert a["active_shares"] == pytest.approx(0.0, abs=1e-9) and a["active_flow"] == pytest.approx(0.0, abs=1e-6)


def test_active_flow_keeps_the_part_of_a_trade_beyond_the_funds_own_scaling():
    cur = {"F1": [h("A", 150, 1500), h("B", 55, 550), h("C", 11, 110)]}
    prev = {"F1": [h("A", 100, 1000), h("B", 50, 500), h("C", 10, 100)]}     # median ratio 1.1 (B and C); A +50%
    a = stock(aggregate_stocks(cur, prev), "A")
    assert a["active_shares"] == pytest.approx(150 - 100 * 1.1) and a["active_flow"] == pytest.approx(400.0)


def test_stock_nobody_holds_any_more_is_flagged_gone_not_sold():
    prev = {f"F{i}": [h("Z", 10, 100)] for i in range(6)}
    cur = {f"F{i}": [h("A", 1, 10)] for i in range(6)}
    rows = aggregate_stocks(cur, prev)
    assert stock(rows, "Z")["gone"] is True and stock(rows, "A")["gone"] is False


def ratios_to_funds(rs):
    cur = {f"F{i}": [h("X", 100 * r, 1000 * r)] for i, r in enumerate(rs)}
    prev = {f"F{i}": [h("X", 100, 500)] for i in range(len(rs))}
    return cur, prev


def test_split_found_even_when_funds_also_traded_around_it():
    # shaped like KLA Corp in the real filings: median ~10x, only a minority within +/-3%
    cur, prev = ratios_to_funds([7.9, 8.4, 9.6, 9.9, 10.0, 10.0, 10.2, 10.7, 11.3, 16.5, 9.98, 12.0])
    assert split_factors(cur, prev)["X"] == 10.0                    # snapped to the usual 10-for-1


def test_split_is_snapped_to_a_standard_ratio_and_rejects_non_standard_medians():
    cur, prev = ratios_to_funds([22, 24, 24.5, 25, 26, 27, 28, 21, 25.5, 24.8])
    assert split_factors(cur, prev)["X"] == 25.0
    cur, prev = ratios_to_funds([2.6] * 10)                         # 2.6x is no ordinary split ratio
    assert split_factors(cur, prev) == {}


def test_widely_scattered_ratios_around_two_are_not_a_split():
    cur, prev = ratios_to_funds([0.5, 1.0, 2.0, 2.0, 2.0, 4.0, 5.0, 1.5, 3.5, 2.5])
    assert split_factors(cur, prev) == {}


def test_overview_lists_detected_splits_with_the_issuer_name(tmp_path):
    cur, prev = str(tmp_path / "q2.zip"), str(tmp_path / "q1.zip")
    funds_cur = {f"000000000{i}": (f"A{i}", f"Fund {i}", 1000, [("SPLITCO INC", "S", 400, 40)]) for i in range(1, 7)}
    funds_prev = {f"000000000{i}": (f"B{i}", f"Fund {i}", 900, [("SPLITCO INC", "S", 100, 10)]) for i in range(1, 7)}
    make_zip(cur, "2026-06-30", funds_cur)
    make_zip(prev, "2026-03-31", funds_prev)
    o = build_overview(cur, prev, "2026-06-30", "2026-03-31", top=10, figi=FakeInfo())
    assert o["splits"] == [{"cusip": "S", "factor": 4.0, "issuer": "SPLITCO INC"}]
    s = next(x for x in o["stocks"] if x["cusip"] == "S")
    assert s["added"] == 0 and s["reduced"] == 0 and s["net_shares"] == pytest.approx(0.0, abs=1e-6)


def funds_holding(cusip, n, prefix):
    return {f"{prefix}{i}": [h(cusip, 10, 100)] for i in range(n)}


def test_a_stock_nearly_everyone_dropped_is_gone_even_if_a_couple_of_funds_still_hold_it():
    prev = funds_holding("Z", 66, "F")
    cur = {k: [h("OTHER", 1, 1)] for k in prev}
    cur["F0"] = [h("Z", 10, 100)]                              # 1 of 66 still has it (e.g. merger arbitrage)
    rows = aggregate_stocks(cur, prev)
    assert stock(rows, "Z")["gone"] is True
    prev2 = funds_holding("Y", 20, "G")
    cur2 = {k: [h("Y", 10, 100)] for k in list(prev2)[:15]} | {k: [h("O", 1, 1)] for k in list(prev2)[15:]}
    assert stock(aggregate_stocks(cur2, prev2), "Y")["gone"] is False       # 15 of 20 kept it: ordinary selling
    prev3 = funds_holding("W", 4, "H")
    assert stock(aggregate_stocks({k: [h("O", 1, 1)] for k in prev3}, prev3), "W")["gone"] is False   # too few holders to judge


def test_a_stock_that_suddenly_appears_at_many_funds_is_flagged_new_listing():
    base = funds_holding("OLD", 30, "F")                       # everyone held something else last quarter
    cur = {k: [h("OLD", 1, 1), h("SPIN", 5, 50)] for k in base}
    prev = {k: [h("OLD", 1, 1)] for k in base}
    s = stock(aggregate_stocks(cur, prev), "SPIN")
    assert s["new_listing"] is True and s["new"] == 30
    prev["F0"].append(h("SPIN", 5, 50))                        # 1 of 30 already held it: spin-off/CUSIP change
    assert stock(aggregate_stocks(cur, prev), "SPIN")["new_listing"] is True
    for k in list(prev)[:20]:                                  # 20 of 30 already held it: ordinary accumulation
        prev[k].append(h("SPIN", 5, 50))
    assert stock(aggregate_stocks(cur, prev), "SPIN")["new_listing"] is False
    small = {f"S{i}": [h("T", 1, 1)] for i in range(10)}
    assert stock(aggregate_stocks(small, {k: [h("OLD", 1, 1)] for k in small}), "T")["new_listing"] is False   # too few funds
