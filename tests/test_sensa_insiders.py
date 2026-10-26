import io

import pytest

from sensa.insiders import aggregate, load_trades

SUB_H = ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERNAME", "ISSUERTRADINGSYMBOL", "AFF10B5ONE"]
OWN_H = ["ACCESSION_NUMBER", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"]
TR_H = ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"]


def tsv(head, *rows):
    return io.StringIO("\t".join(head) + "\n" + "".join("\t".join(r) + "\n" for r in rows))


def sample():
    sub = tsv(SUB_H,
              ["A1", "02-SEP-2026", "4", "1", "Acme Corp", "ACME", "0"],
              ["A2", "03-SEP-2026", "4", "1", "Acme Corp", "ACME", "1"],            # 10b5-1 plan sale
              ["A3", "04-SEP-2026", "4/A", "1", "Acme Corp", "ACME", "0"],          # amendment: skipped
              ["A4", "05-SEP-2026", "4", "2", "No Ticker Inc", "", "0"],            # no trading symbol: skipped
              ["A5", "06-SEP-2026", "4", "3", "Beta Co", "beta", "0"],
              ["A6", "06-SEP-2026", "3", "3", "Beta Co", "BETA", "0"])              # Form 3: not a trade report
    own = tsv(OWN_H,
              ["A1", "Doe Jane", "Officer", "CFO"], ["A2", "Roe Rich", "Director", ""],
              ["A3", "Doe Jane", "Officer", "CFO"], ["A4", "X Y", "Director", ""],
              ["A5", "Poe Pat", "Officer,Director", "Chief Exec Officer"], ["A5", "Poe Holdings LLC", "TenPercentOwner", ""],
              ["A6", "Z", "Director", ""])
    tr = tsv(TR_H,
             ["A1", "01-SEP-2026", "P", "1000", "12.5", "A"],
             ["A1", "01-SEP-2026", "P", "500", "13.5", "A"],                         # same day, same insider: merged
             ["A1", "01-SEP-2026", "A", "99", "0", "A"],                             # grant: not an open-market trade
             ["A2", "02-SEP-2026", "S", "200", "50", "D"],
             ["A3", "03-SEP-2026", "P", "10", "1", "A"],
             ["A4", "04-SEP-2026", "P", "10", "1", "A"],
             ["A5", "05-SEP-2026", "P", "100", "", "A"],                             # no price: skipped
             ["A5", "05-SEP-2026", "P", "100", "20", "A"])
    return sub, own, tr


def test_load_trades_keeps_open_market_trades_of_form_4_with_a_symbol_and_merges_same_day_lines():
    t = load_trades(*sample())
    by = {(x["symbol"], x["owner"], x["side"]): x for x in t}
    acme_buy = by[("ACME", "Doe Jane", "buy")]
    assert acme_buy["shares"] == 1500.0 and acme_buy["value"] == 12.5 * 1000 + 13.5 * 500
    assert acme_buy["price"] == pytest.approx(acme_buy["value"] / 1500) and acme_buy["role"] == "CFO"
    assert acme_buy["date"] == "2026-09-01" and acme_buy["filed"] == "2026-09-02" and acme_buy["issuer"] == "Acme Corp"
    sale = by[("ACME", "Roe Rich", "sell")]
    assert sale["role"] == "Director" and sale["plan"] is True and sale["value"] == 10000.0
    assert acme_buy["plan"] is False
    assert len(t) == 3                                       # 4/A, no-symbol, Form 3, grant and priceless lines are out


def test_symbol_is_upper_cased_and_all_owners_are_named():
    t = load_trades(*sample())
    beta = next(x for x in t if x["symbol"] == "BETA")
    assert beta["owner"] == "Poe Holdings LLC / Poe Pat" and beta["role"] == "Chief Exec Officer" and beta["value"] == 2000.0


def trade(symbol, owner, side, value, date="2026-09-10", plan=False, role="CEO", shares=100.0):
    return {"symbol": symbol, "issuer": symbol + " Inc", "owner": owner, "role": role, "side": side, "value": float(value),
            "shares": shares, "price": value / shares, "date": date, "filed": date, "accession": "a", "plan": plan}


def test_aggregate_ranks_top_buys_and_sells_inside_the_window():
    ts = [trade("AAA", "p1", "buy", 500), trade("BBB", "p2", "buy", 900), trade("CCC", "p3", "sell", 700),
          trade("DDD", "p4", "sell", 300), trade("OLD", "p5", "buy", 99999, date="2026-06-01")]
    a = aggregate(ts, as_of="2026-09-30", days=30, top=2)
    assert [x["symbol"] for x in a["top_buys"]] == ["BBB", "AAA"] and [x["symbol"] for x in a["top_sells"]] == ["CCC", "DDD"]
    assert a["buy_value"] == 1400.0 and a["sell_value"] == 1000.0 and a["trades"] == 4


def test_cluster_buys_need_several_distinct_insiders_and_ignore_sales():
    ts = [trade("CL", "p1", "buy", 100), trade("CL", "p2", "buy", 200, date="2026-09-12"), trade("CL", "p3", "buy", 300, date="2026-09-20"),
          trade("CL", "p1", "buy", 50, date="2026-09-21"),                       # repeat buyer: still 3 insiders
          trade("TWO", "p1", "buy", 999), trade("TWO", "p2", "buy", 999),        # only two insiders
          trade("SEL", "p1", "sell", 5), trade("SEL", "p2", "sell", 5), trade("SEL", "p3", "sell", 5)]
    a = aggregate(ts, as_of="2026-09-30", days=30, min_insiders=3)
    assert [c["symbol"] for c in a["clusters"]] == ["CL"]
    c = a["clusters"][0]
    assert c["insiders"] == 3 and c["value"] == 650.0 and c["last"] == "2026-09-21" and c["trades"] == 4


def test_plan_sales_can_be_excluded_from_the_sell_ranking():
    ts = [trade("AAA", "p1", "sell", 900, plan=True), trade("BBB", "p2", "sell", 100)]
    assert [x["symbol"] for x in aggregate(ts, "2026-09-30", 30, include_plans=True)["top_sells"]] == ["AAA", "BBB"]
    assert [x["symbol"] for x in aggregate(ts, "2026-09-30", 30, include_plans=False)["top_sells"]] == ["BBB"]


import zipfile

from markov.data_providers import DataUnavailable
from sensa.insiders import InsiderService, find_insider_sets, load_insiders, refresh_insiders

LISTING = ('<a href="/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q3_form345.zip">a</a>'
           '<a href="/files/structureddata/data/insider-transactions-data-sets/2026q1_form345.zip">c</a>'
           '<a href="/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q2_form345.zip">b</a>')


def write_zip(path):
    sub, own, tr = sample()
    parts = {"SUBMISSION.tsv": sub, "REPORTINGOWNER.tsv": own, "NONDERIV_TRANS.tsv": tr}
    with zipfile.ZipFile(path, "w") as z:
        for name, fh in parts.items():
            z.writestr(name, fh.getvalue())


def downloader(log):
    def dl(url, dest):
        log.append(url)
        write_zip(dest)
    return dl


def test_find_insider_sets_orders_quarters_newest_first_and_ignores_other_links():
    sets = find_insider_sets(LISTING + '<a href="/files/x/other.zip">z</a>')
    assert [s["quarter"] for s in sets] == ["2026q3", "2026q2", "2026q1"]
    assert sets[0]["label"] == "Q3 2026" and sets[0]["url"].startswith("https://www.sec.gov/files/datastandardsinnovation/")


def test_refresh_builds_stores_and_is_a_no_op_until_a_newer_quarter(tmp_path):
    log = []
    d = refresh_insiders(str(tmp_path), LISTING, downloader(log), min_value=0)
    assert d["quarter"] == "Q3 2026" and d["as_of"] == "2026-09-06" and len(d["trades"]) == 3
    assert load_insiders(str(tmp_path))["trades"][0]["symbol"] in ("ACME", "BETA")
    assert refresh_insiders(str(tmp_path), LISTING, downloader(log), min_value=0) is None and len(log) == 1
    assert refresh_insiders(str(tmp_path), LISTING, downloader(log), min_value=0, force=True) is not None and len(log) == 1   # zip reused


def test_refresh_drops_trades_below_the_minimum_value(tmp_path):
    d = refresh_insiders(str(tmp_path), LISTING, downloader([]), min_value=5000)
    assert {t["symbol"] for t in d["trades"]} == {"ACME"} and all(t["value"] >= 5000 for t in d["trades"])


def test_failed_download_keeps_the_previous_good_data(tmp_path):
    refresh_insiders(str(tmp_path), LISTING, downloader([]), min_value=0)
    for p in (tmp_path / "zips").glob("*.zip"):
        p.unlink()

    def broken(url, dest):
        raise DataUnavailable("network down")
    import pytest as _p
    with _p.raises(DataUnavailable):
        refresh_insiders(str(tmp_path), LISTING, broken, min_value=0, force=True)
    assert load_insiders(str(tmp_path))["quarter"] == "Q3 2026"


def test_load_insiders_without_a_build_says_to_press_update(tmp_path):
    import pytest as _p
    with _p.raises(DataUnavailable, match="Update"):
        load_insiders(str(tmp_path))


def test_service_overview_and_symbol_views(tmp_path):
    svc = InsiderService(str(tmp_path), lambda: LISTING, downloader([]), min_value=0)
    svc.start()
    svc.wait(10)
    assert svc.state()["state"] == "done"
    o = svc.overview(days=30)
    assert o["quarter"] == "Q3 2026" and o["top_buys"][0]["symbol"] in ("ACME", "BETA") and o["as_of"] == "2026-09-06"
    s = svc.symbol("acme")
    assert s["symbol"] == "ACME" and [t["side"] for t in s["trades"]] == ["sell", "buy"]            # newest first
    assert svc.symbol("NOPE")["trades"] == []
    assert svc.status()["quarter"] == "Q3 2026"


def test_same_trade_reported_by_joint_filers_counts_once_with_all_owner_names():
    sub = tsv(SUB_H, ["J1", "10-SEP-2026", "4", "1", "Lennar", "LEN", "0"], ["J2", "10-SEP-2026", "4", "1", "Lennar", "LEN", "0"],
              ["K1", "10-SEP-2026", "4", "2", "Other", "OTH", "0"], ["K2", "10-SEP-2026", "4", "2", "Other", "OTH", "0"])
    own = tsv(OWN_H, ["J1", "BERKSHIRE HATHAWAY INC", "TenPercentOwner", ""], ["J2", "BUFFETT WARREN E", "Director", ""],
              ["K1", "Alice A", "Officer", "CEO"], ["K2", "Bob B", "Officer", "CFO"])
    tr = tsv(TR_H, ["J1", "09-SEP-2026", "P", "1000", "100", "A"], ["J2", "09-SEP-2026", "P", "1000", "100", "A"],
             ["K1", "09-SEP-2026", "P", "100", "10", "A"], ["K2", "09-SEP-2026", "P", "200", "10", "A"])      # different sizes: two real buys
    t = load_trades(sub, own, tr)
    len_ = [x for x in t if x["symbol"] == "LEN"]
    assert len(len_) == 1 and len_[0]["value"] == 100000.0 and len_[0]["owner"] == "BERKSHIRE HATHAWAY INC / BUFFETT WARREN E"
    assert len([x for x in t if x["symbol"] == "OTH"]) == 2


def test_multi_class_symbol_field_uses_the_first_ticker_and_placeholders_are_dropped():
    sub = tsv(SUB_H, ["M1", "10-SEP-2026", "4", "1", "Lennar", "LEN, LEN.B", "0"], ["M2", "10-SEP-2026", "4", "2", "Nobody", "N/A", "0"],
              ["M3", "10-SEP-2026", "4", "3", "Dash", "-", "0"], ["M4", "10-SEP-2026", "4", "4", "Slash", "brk/b brk/a", "0"])
    own = tsv(OWN_H, *[[a, "X", "Officer", "CEO"] for a in ("M1", "M2", "M3", "M4")])
    tr = tsv(TR_H, *[[a, "09-SEP-2026", "P", "10", "10", "A"] for a in ("M1", "M2", "M3", "M4")])
    assert sorted(x["symbol"] for x in load_trades(sub, own, tr)) == ["BRK/B", "LEN"]


def test_cluster_counts_individual_people_even_when_one_row_has_joint_owners():
    ts = [trade("CL", "Alice / Bob", "buy", 100), trade("CL", "Carol", "buy", 100, date="2026-09-12")]
    c = aggregate(ts, "2026-09-30", 30, min_insiders=3)["clusters"]
    assert c and c[0]["insiders"] == 3


def test_same_people_listed_in_a_different_order_are_one_insider_in_the_rankings():
    sub = tsv(SUB_H, ["L1", "10-SEP-2026", "4", "1", "Lennar", "LEN", "0"], ["L2", "11-SEP-2026", "4", "1", "Lennar", "LEN", "0"])
    own = tsv(OWN_H, ["L1", "BERKSHIRE HATHAWAY INC", "TenPercentOwner", ""], ["L1", "BUFFETT WARREN E", "Director", ""],
              ["L2", "BUFFETT WARREN E", "Director", ""], ["L2", "BERKSHIRE HATHAWAY INC", "TenPercentOwner", ""])
    tr = tsv(TR_H, ["L1", "09-SEP-2026", "P", "1000", "100", "A"], ["L2", "10-SEP-2026", "P", "500", "200", "A"])
    t = load_trades(sub, own, tr)
    assert {x["owner"] for x in t} == {"BERKSHIRE HATHAWAY INC / BUFFETT WARREN E"}
    a = aggregate(t, "2026-09-30", 30)
    assert len(a["top_buys"]) == 1 and a["top_buys"][0]["value"] == 200000.0 and a["top_buys"][0]["trades"] == 2


def test_load_trades_records_the_balance_after_the_trade_from_direct_holding_lines_only():
    head = TR_H + ["SHRSOWNFOLWNG", "DIRECT_INDIRECT_OWNERSHIP"]
    sub = tsv(SUB_H, ["B1", "02-SEP-2026", "4", "1", "Acme Corp", "ACME", "0"])
    own = tsv(OWN_H, ["B1", "Doe Jane", "Officer", "CFO"])
    tr = tsv(head,
             ["B1", "01-SEP-2026", "P", "100", "10", "A", "1100", "D"],
             ["B1", "01-SEP-2026", "P", "50", "10", "A", "1150", "D"],               # later line, same day: final balance
             ["B1", "01-SEP-2026", "S", "5", "10", "D", "999", "I"])                   # indirect holding: not the person's own balance
    t = {x["side"]: x for x in load_trades(sub, own, tr)}
    assert t["buy"]["owned_after"] == 1150.0 and t["sell"]["owned_after"] is None


def test_load_trades_without_balance_columns_still_works():
    t = load_trades(*sample())
    assert all(x["owned_after"] is None for x in t)


def test_service_exposes_recent_trades_for_performance_work(tmp_path):
    svc = InsiderService(str(tmp_path), lambda: LISTING, downloader([]), min_value=0)
    svc.start()
    svc.wait(10)
    t = svc.trades_since(days=30)
    assert t and all(x["date"] >= "2026-08-07" for x in t) and svc.trades_since(days=0) == []
