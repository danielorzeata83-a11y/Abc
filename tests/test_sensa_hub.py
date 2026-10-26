import pytest

from markov.data_providers import DataUnavailable
from sensa.hub import Hub


class FakeCboe:
    def __init__(self):
        self.quote_calls = 0

    def quote(self, sym):
        self.quote_calls += 1
        return {"AAA": {"price": 110.0, "prev_close": 100.0},
                "BBB": {"price": 90.0, "prev_close": 100.0}}[sym]

    def chain(self, sym):
        row = lambda t, exp, k: {"option_type": t, "strike": k, "expiration": exp, "gamma": 0.01,
                                 "open_interest": 10, "volume": 4 if t == "call" else 2}
        return 100.0, [row("call", "2026-11-20", 100.0), row("put", "2026-11-20", 100.0),
                       row("call", "2026-10-26", 100.0), row("put", "2026-10-26", 100.0),
                       row("call", "2026-10-26", 500.0)]   # far-OTM strike


class FakeAnalyst:
    def recommendations(self, sym):
        return [{"period": "2026-10-01", "strongBuy": 1, "buy": 1, "hold": 0,
                 "sell": 0, "strongSell": 0}]


def make(now=lambda: 0.0, ttl=60, cboe=None, analyst=FakeAnalyst()):
    return Hub(cboe or FakeCboe(), lambda sym: [{"headline": str(i)} for i in range(30)],
               lambda: {"date": "d", "points": []}, analyst=analyst, ttl=ttl, clock=now,
               today=lambda: "2026-10-26")


def test_movers_for_watchlist_uses_cache_within_ttl():
    cb, t = FakeCboe(), [0.0]
    hub = make(lambda: t[0], 60, cb)
    first = hub.movers(["AAA", "BBB"])
    hub.movers(["AAA", "BBB"])
    assert cb.quote_calls == 2                      # second call served from cache
    assert first["gainers"][0]["symbol"] == "AAA"
    t[0] = 61.0
    hub.movers(["AAA", "BBB"])
    assert cb.quote_calls == 4                      # expired -> refetched


def test_movers_drops_a_symbol_whose_quote_fails_instead_of_failing_all():
    class Flaky(FakeCboe):
        def quote(self, sym):
            if sym == "BBB":
                raise DataUnavailable("nope")
            return super().quote(sym)
    out = make(cboe=Flaky()).movers(["AAA", "BBB"])
    assert [r["symbol"] for r in out["gainers"]] == ["AAA"]


def test_options_uses_nearest_expiration_and_flags_zero_dte():
    o = make().options("aaa")
    assert o["expiration"] == "2026-10-26" and o["zero_dte"] is True
    assert o["cp"]["call_volume"] == 8              # only the nearest expiry counted
    assert o["gex"]["net_gex"] == pytest.approx(1000.0)   # 1000 call + 1000 far call - 1000 put
    assert 500.0 not in [r["strike"] for r in o["gex"]["by_strike"]]   # trimmed to +/-15% of spot


def test_options_none_when_no_chain():
    class Empty(FakeCboe):
        def chain(self, sym):
            return 100.0, []
    assert make(cboe=Empty()).options("AAA") is None


def test_news_is_trimmed_to_limit():
    assert len(make().news(limit=10)) == 10


def test_analyst_is_none_when_not_configured_or_no_data():
    assert make(analyst=None).analyst("AAA") is None
    class Empty(FakeAnalyst):
        def recommendations(self, sym):
            return []
    assert make(analyst=Empty()).analyst("AAA") is None


class FakeEdgar:
    def __init__(self):
        self.calls = 0

    def recent(self, symbol=None, limit=10):
        self.calls += 1
        return [{"symbol": symbol or "ACME", "side": "buy"}]


def test_insiders_cached_for_five_minutes_regardless_of_short_ttl():
    ed, t = FakeEdgar(), [0.0]
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, edgar=ed, ttl=60, clock=lambda: t[0])
    hub.insiders(); t[0] = 120.0; hub.insiders()
    assert ed.calls == 1                       # 120s < 300s insider ttl
    t[0] = 400.0; hub.insiders()
    assert ed.calls == 2


def test_insiders_unavailable_without_edgar():
    import pytest as _p
    with _p.raises(DataUnavailable):
        make().insiders()


def test_sectors_skips_failed_quotes_and_uses_cache():
    class Sec(FakeCboe):
        def quote(self, sym):
            self.quote_calls += 1
            if sym == "XLE":
                raise DataUnavailable("x")
            return {"price": 101.0, "prev_close": 100.0}
    cb = Sec()
    hub = make(cboe=cb)
    out = hub.sectors()
    assert len(out) == 10 and all(r["change_pct"] == 1.0 for r in out)
    n = cb.quote_calls
    hub.sectors()
    assert cb.quote_calls == n + 1          # only the failed XLE is retried; the rest is cached


def test_short_volume_parses_file_once_per_hour_and_looks_up_symbols():
    class Fin:
        loads = 0
        def load(self, today):
            Fin.loads += 1
            return {"date": "2026-10-23", "rows": {"AAA": (30.0, 100.0)}}
        lookup = staticmethod(__import__("sensa.finra", fromlist=["Finra"]).Finra.lookup)
    t = [0.0]
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, finra=Fin(), ttl=60, clock=lambda: t[0],
              today=lambda: "2026-10-26")
    assert hub.short_volume("aaa")["short_ratio"] == 0.3
    t[0] = 1800.0
    assert hub.short_volume("ZZZ") is None
    assert Fin.loads == 1
    t[0] = 4000.0
    hub.short_volume("AAA")
    assert Fin.loads == 2


def test_candles_delegates_validates_timeframe_and_caches():
    calls = []

    def candles(sym, tf):
        calls.append((sym, tf))
        return [{"time": 1, "open": 1, "high": 2, "low": 0, "close": 1, "volume": 3}]
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, candles_fn=candles, ttl=60)
    assert hub.candles("aaa", "1h")[0]["close"] == 1
    hub.candles("AAA", "1h")
    assert calls == [("AAA", "1h")]
    import pytest as _p
    with _p.raises(ValueError):
        hub.candles("AAA", "7m")


def test_candles_unavailable_when_not_configured():
    import pytest as _p
    with _p.raises(DataUnavailable):
        make().candles("AAA", "1h")


def test_daily_candles_are_cached_for_hours_to_protect_the_free_quota():
    calls, t = [], [0.0]
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, ttl=60, clock=lambda: t[0],
              candles_fn=lambda s, tf: calls.append((s, tf)) or [{"time": "2026-10-23"}])
    hub.candles("AAA", "1day")
    t[0] = 3 * 3600
    hub.candles("AAA", "1day")
    assert len(calls) == 1
    t[0] = 7 * 3600
    hub.candles("AAA", "1day")
    assert len(calls) == 2


def test_failed_candle_fetch_is_remembered_for_five_minutes():
    calls, t = [], [0.0]

    def boom(s, tf):
        calls.append(1)
        raise DataUnavailable("rate limited")
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, ttl=60, clock=lambda: t[0], candles_fn=boom)
    import pytest as _p
    for _ in range(2):
        with _p.raises(DataUnavailable, match="rate limited"):
            hub.candles("AAA", "1day")
    assert len(calls) == 1                     # second raise came from the failure cache
    t[0] = 301.0
    with _p.raises(DataUnavailable):
        hub.candles("AAA", "1day")
    assert len(calls) == 2


class Fake13F:
    def __init__(self):
        self.holding_calls = []
        self.data = {
            "A2": [{"issuer": "AMAZON COM INC", "cusip": "C1", "value": 600.0, "shares": 20.0},
                   {"issuer": "ACME CORP", "cusip": "C2", "value": 300.0, "shares": 5.0},
                   {"issuer": "NEWCO", "cusip": "C3", "value": 100.0, "shares": 1.0}],
            "A1": [{"issuer": "AMAZON COM INC", "cusip": "C1", "value": 400.0, "shares": 10.0},
                   {"issuer": "ACME CORP", "cusip": "C2", "value": 300.0, "shares": 9.0},
                   {"issuer": "GONE INC", "cusip": "C4", "value": 100.0, "shares": 2.0}],
        }

    def filer(self, cik):
        f = lambda q, p, d, a: {"quarter": q, "period": p, "filed": d, "accession": a, "form": "13F-HR"}
        return {"cik": "0000000001", "name": "Test Capital LP", "location": "New York, NY",
                "filings": [f("Q2 2026", "2026-06-30", "2026-08-14", "A2"),
                            f("Q1 2026", "2026-03-31", "2026-05-15", "A1")]}

    def holdings(self, cik, acc, filed=None):
        self.holding_calls.append(acc)
        return self.data[acc]


class FakeFigi:
    def lookup(self, cusips):
        return {"C1": "AMZN", "C2": "ACME", "C3": "NEW"}


def mgr_hub(f13=None):
    return Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f13 or Fake13F(), figi=FakeFigi())


def test_manager_overview_stats_allocation_and_activity():
    m = mgr_hub().manager("1")
    assert m["name"] == "Test Capital LP" and m["latest"]["quarter"] == "Q2 2026"
    assert m["stats"]["value"] == 1000.0 and m["stats"]["value_change"] == 200.0
    assert m["stats"]["value_change_pct"] == 25.0
    assert m["stats"]["holdings"] == 3 and m["stats"]["holdings_change"] == 0
    assert m["stats"]["filings"] == 2 and m["stats"]["since"] == "2026"
    assert [h["ticker"] for h in m["top"]] == ["AMZN", "ACME", "NEW"]
    assert m["top"][0]["weight"] == 60.0
    assert m["allocation"][0] == {"ticker": "AMZN", "name": "AMAZON COM INC", "value": 600.0, "weight": 60.0}
    assert m["activity"] == {"new": 1, "increased": 1, "reduced": 1, "exited": 1}


def test_manager_filing_rows_are_paged_and_cached_forever():
    f = Fake13F()
    hub = mgr_hub(f)
    page = hub.manager_filings("1", offset=0, limit=20)
    assert page["total"] == 2
    assert page["rows"][0] == {"quarter": "Q2 2026", "holdings": 3, "value": 1000.0,
                               "top": ["AMZN", "ACME", "NEW"], "form": "13F-HR",
                               "filed": "2026-08-14", "accession": "A2"}
    hub.manager_filings("1", 0, 20); hub.manager("1")
    assert sorted(f.holding_calls) == ["A1", "A2"]         # each filing fetched once
    assert hub.manager_filings("1", offset=1, limit=1)["rows"][0]["quarter"] == "Q1 2026"


def test_manager_unavailable_without_sec_client():
    with pytest.raises(DataUnavailable):
        make().manager("1")


def test_manager_since_is_the_year_the_first_filing_was_made_not_its_period():
    class Old(Fake13F):
        def filer(self, cik):
            f = super().filer(cik)
            f["filings"].append({"quarter": "Q4 2014", "period": "2014-12-31", "filed": "2015-02-14",
                                 "accession": "A0", "form": "13F-HR"})
            return f
    assert mgr_hub(Old()).manager("1")["stats"]["since"] == "2015"


def test_manager_filings_downloads_filings_concurrently():
    import threading

    class Slow(Fake13F):
        def __init__(self):
            super().__init__()
            self.gate = threading.Barrier(2, timeout=3)   # both fetches must be in flight together

        def holdings(self, cik, acc, filed=None):
            self.gate.wait()                               # BrokenBarrierError if run one-by-one
            return super().holdings(cik, acc, filed)
    page = mgr_hub(Slow()).manager_filings("1", 0, 20)
    assert [r["quarter"] for r in page["rows"]] == ["Q2 2026", "Q1 2026"]


def test_manager_overview_fetches_current_and_previous_quarter_concurrently():
    import threading

    class Slow(Fake13F):
        def __init__(self):
            super().__init__()
            self.gate = threading.Barrier(2, timeout=3)

        def holdings(self, cik, acc, filed=None):
            self.gate.wait()
            return super().holdings(cik, acc, filed)
    assert mgr_hub(Slow()).manager("1")["stats"]["holdings"] == 3


def test_unmapped_cusip_falls_back_to_a_short_issuer_name_not_the_raw_code():
    class NoFigi:
        def lookup(self, cusips):
            return {}
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=Fake13F(), figi=NoFigi())
    top = hub.manager("1")["top"]
    assert top[0]["ticker"] == "AMAZON COM I"[:12] and not top[0]["ticker"].startswith("C")


def test_filings_are_cached_on_disk_so_a_fresh_hub_needs_no_sec_requests(tmp_path):
    f1 = Fake13F()
    h1 = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f1, figi=FakeFigi(), cache_dir=str(tmp_path))
    h1.manager_filings("1", 0, 20)
    assert sorted(f1.holding_calls) == ["A1", "A2"]
    f2 = Fake13F()
    h2 = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f2, figi=FakeFigi(), cache_dir=str(tmp_path))
    page = h2.manager_filings("1", 0, 20)
    assert f2.holding_calls == [] and page["rows"][0]["value"] == 1000.0     # served from disk


def test_corrupt_disk_cache_entry_is_ignored_and_refetched(tmp_path):
    f1 = Fake13F()
    h1 = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f1, figi=FakeFigi(), cache_dir=str(tmp_path))
    h1.manager_filings("1", 0, 20)
    for p in tmp_path.rglob("*.json"):
        p.write_text("{not json")
    f2 = Fake13F()
    h2 = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f2, figi=FakeFigi(), cache_dir=str(tmp_path))
    assert h2.manager_filings("1", 0, 20)["rows"][0]["holdings"] == 3
    assert sorted(f2.holding_calls) == ["A1", "A2"]


def test_disk_cache_rejects_path_traversal_in_identifiers(tmp_path):
    h = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=Fake13F(), figi=FakeFigi(), cache_dir=str(tmp_path))
    with pytest.raises(ValueError):
        h._raw("../../etc", {"accession": "A1", "filed": "2026-01-01"})
    with pytest.raises(ValueError):
        h._raw("1", {"accession": "../x", "filed": "2026-01-01"})


def test_fund_header_data_refreshes_after_ten_minutes_but_not_before():
    f, t = Fake13F(), [0.0]
    calls = []
    orig = f.filer
    f.filer = lambda cik: calls.append(1) or orig(cik)
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f, figi=FakeFigi(), clock=lambda: t[0])
    hub.manager("1"); t[0] = 300.0; hub.manager("1")
    assert len(calls) == 1
    t[0] = 700.0; hub.manager("1")
    assert len(calls) == 2


class Latest13F(Fake13F):
    def __init__(self):
        super().__init__()
        self.cover_calls = []

    def latest(self, limit=50, scan=100):
        return [{"cik": "0000000001", "name": "Test Capital LP", "form": "13F-HR", "filed": "2026-10-26",
                 "accession": "0000000001-26-000007"},
                {"cik": "0000000002", "name": "Other Fund", "form": "13F-HR", "filed": "2026-10-25",
                 "accession": "0000000002-26-000003"}][:limit]

    def cover(self, cik, accession, filed=None):
        self.cover_calls.append(accession)
        return {"period": "2026-09-30", "quarter": "Q3 2026", "entries": 71 if accession.endswith("7") else 5,
                "value": 297e6, "name": "n"}


def test_latest_filings_adds_cover_data_registers_accessions_and_caches_on_disk(tmp_path):
    f = Latest13F()
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f, figi=FakeFigi(), cache_dir=str(tmp_path))
    rows = hub.latest_filings(10)
    assert rows[0] == {"cik": "0000000001", "name": "Test Capital LP", "form": "13F-HR", "filed": "2026-10-26",
                       "accession": "0000000001-26-000007", "quarter": "Q3 2026", "period": "2026-09-30",
                       "entries": 71, "value": 297e6}
    assert hub.cik_for_accession("000000000126000007") == ("0000000001", "0000000001-26-000007")
    f2 = Latest13F()
    Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=f2, figi=FakeFigi(),
        cache_dir=str(tmp_path)).latest_filings(10)
    assert f2.cover_calls == []                         # covers came from disk


def test_a_cover_that_fails_does_not_hide_the_row(tmp_path):
    class Flaky(Latest13F):
        def cover(self, cik, accession, filed=None):
            raise DataUnavailable("sec slow")
    rows = Hub(FakeCboe(), lambda s: [], lambda: None, thirteenf=Flaky(), figi=FakeFigi()).latest_filings(10)
    assert [r["name"] for r in rows] == ["Test Capital LP", "Other Fund"] and rows[0]["entries"] is None


def test_filing_page_data_compares_with_the_prior_quarter_and_lists_holdings():
    hub = mgr_hub()
    hub.manager("1")                                    # registers the fund's accessions
    d = hub.filing("A2")
    assert d["name"] == "Test Capital LP" and d["quarter"] == "Q2 2026" and d["form"] == "13F-HR"
    assert d["stats"]["value"] == 1000.0 and d["stats"]["positions"] == 3 and d["stats"]["value_change"] == 200.0
    top = d["holdings"][0]
    assert top["ticker"] == "AMZN" and top["weight"] == 60.0
    assert top["change"] == {"type": "increased", "shares_delta": 10.0, "pct": 100.0}
    new = next(h for h in d["holdings"] if h["ticker"] == "NEW")
    assert new["change"]["type"] == "new" and new["change"]["pct"] is None
    assert d["exited"][0]["issuer"] == "GONE INC"       # positions dropped since the previous filing


def test_unknown_accession_is_reported_not_guessed():
    import pytest as _p
    with _p.raises(DataUnavailable, match="not found"):
        mgr_hub().filing("999999999999999999")


def test_quote_returns_the_full_quote_and_shares_the_cache_with_movers():
    cb = FakeCboe()
    hub = make(cboe=cb)
    hub.movers(["AAA"])
    assert hub.quote("aaa")["price"] == 110.0 and cb.quote_calls == 1


def test_quote_of_an_unknown_symbol_raises_data_unavailable():
    class NoQuote(FakeCboe):
        def quote(self, sym):
            raise DataUnavailable("no such symbol")
    with pytest.raises(DataUnavailable):
        make(cboe=NoQuote()).quote("ZZZ")


def test_company_comes_from_the_injected_source_or_is_none():
    hub = Hub(FakeCboe(), lambda s: [], lambda: None, company_fn=lambda t: {"ticker": t, "name": "X"})
    assert hub.company("aaa") == {"ticker": "AAA", "name": "X"}
    assert make().company("AAA") is None
