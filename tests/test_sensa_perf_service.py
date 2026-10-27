import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.perf_service import PerfJob, PortfolioService
from tests.test_sensa_holders import db  # noqa: F401
from tests.test_sensa_performance import Prices

SERIES = {"PEBO": [("2026-06-30", 10.0), ("2026-08-14", 12.0), ("2026-10-23", 15.0)],
          "SPY": [("2026-06-30", 100.0), ("2026-08-14", 105.0), ("2026-10-23", 110.0)]}


class FakeBook(Prices):
    def __init__(self):
        super().__init__(SERIES)
        self.warmed = []

    def warm(self, tickers):
        self.warmed.extend(tickers)


class Figi:
    def info(self, cusips):
        return {c: {"ticker": "PEBO", "kind": "stock"} for c in cusips if c == "709789101"}


def test_perf_job_writes_the_result_and_serves_it_with_its_timestamp(tmp_path):
    job = PerfJob("computing", lambda: {"rows": [1, 2]}, str(tmp_path / "p.json"))
    with pytest.raises(DataUnavailable, match="not computed yet"):
        job.result()
    job.start()
    job.wait(10)
    r = job.result()
    assert r["data"] == {"rows": [1, 2]} and r["generated"] and job.status()["state"] == "done"
    assert job.status()["generated"] == r["generated"]


def test_perf_job_reports_errors_and_keeps_the_last_good_result(tmp_path):
    path = str(tmp_path / "p.json")
    ok = PerfJob("c", lambda: {"v": 1}, path)
    ok.start(); ok.wait(10)

    def boom():
        raise DataUnavailable("no prices")
    bad = PerfJob("c", boom, path)
    bad.start(); bad.wait(10)
    assert bad.status()["state"] == "error" and "no prices" in bad.status()["message"] and bad.result()["data"] == {"v": 1}


def test_portfolio_service_values_a_filers_positions_at_todays_prices(db):
    book = FakeBook()
    svc = PortfolioService(db, None, Figi(), book)
    r = svc.fund("0000000001")
    assert r["name"] == "Alpha Fund" and r["period"] == "2026-06-30" and r["filed"] == "2026-08-14"
    assert r["covered_positions"] == 1 and r["rows"][0]["ticker"] == "PEBO"
    assert r["return_since_filing_pct"] == 25.0 and r["return_since_period_pct"] == 50.0
    assert "SPY" in book.warmed and "PEBO" in book.warmed
    with pytest.raises(KeyError):
        svc.fund("0000000042")


from sensa.perf_service import funds_board, insiders_board, members_board


def test_funds_board_ranks_each_top_fund_by_its_return_since_filing():
    class P:
        def fund(self, cik, top_n=None):
            if cik == "gone":
                raise KeyError(cik)
            return {"name": cik.upper(), "period": "p", "filed": "f", "return_since_period_pct": 1.0, "return_since_filing_pct": {"a": 5.0, "b": -2.0}[cik],
                    "spy_since_period_pct": 2.0, "spy_since_filing_pct": 1.0, "covered_pct": 90.0}
    ov = {"funds": [{"rank": 1, "cik": "b", "name": "B", "aum": 2.0}, {"rank": 2, "cik": "gone", "name": "G", "aum": 1.0},
                    {"rank": 3, "cik": "a", "name": "A", "aum": 3.0}]}
    rows = funds_board(ov, P())
    assert [r["cik"] for r in rows] == ["a", "b"] and rows[0]["return_since_filing_pct"] == 5.0 and rows[0]["rank"] == 3


def test_members_board_prices_the_tickers_it_needs_and_scores_the_members():
    book = FakeBook()
    book.s["AAA"] = [("2026-06-30", 10.0), ("2026-10-23", 15.0)]

    class Pol:
        def trades_since(self, days):
            return [{"member": "Ann", "ticker": "AAA", "type": "purchase", "date": "2026-06-30", "filed": "2026-06-30", "value": 1000.0}] * 3
    rows = members_board(Pol(), book)
    assert rows[0]["member"] == "Ann" and rows[0]["return_since_trade_pct"] == 50.0 and set(book.warmed) == {"AAA", "SPY"}


def test_insiders_board_has_buy_performance_and_the_biggest_balances():
    book = FakeBook()
    book.s["AAA"] = [("2026-06-30", 10.0), ("2026-10-23", 15.0)]

    class Ins:
        def trades_since(self, days):
            return [{"owner": "Ann", "symbol": "AAA", "side": "buy", "date": "2026-06-30", "price": 10.0, "shares": 10000.0,
                     "value": 100000.0, "owned_after": 50000.0, "role": "CEO", "issuer": "Acme"},
                    {"owner": "Tiny", "symbol": "BBB", "side": "buy", "date": "2026-06-30", "price": 1.0, "shares": 10.0, "value": 10.0,
                     "owned_after": 10.0, "role": "", "issuer": "B"}]
    d = insiders_board(Ins(), book)
    assert d["performance"]["n"] == 1 and d["performance"]["avg_return_pct"] == 50.0
    assert d["holdings"][0]["owner"] == "Ann" and d["holdings"][0]["value"] == 750000.0 and "BBB" not in book.warmed


from sensa.perf_service import picks_board
from tests.test_picks import Book, overview as pick_overview, row, walk


def test_picks_board_builds_the_picks_and_an_out_of_sample_backtest_of_the_price_rule():
    rows = [row(f"S{i}", 60 + i, 50) for i in range(16)]
    series = {f"S{i}": walk(0.0004 + 0.00006 * i, 0.004, seed=i, n=900) for i in range(16)}
    series["SPY"] = walk(0.0004, 0.008, seed=99, n=900)

    import pandas as pd
    dates = list(pd.bdate_range("2020-01-01", periods=900).strftime("%Y-%m-%d"))

    def adjusted(t, years):
        return list(zip(dates, series[t]))

    class Ins:
        def trades_since(self, d):
            return []

    class Pol:
        def trades_since(self, d):
            raise DataUnavailable("not built")
    out = picks_board(lambda: pick_overview(rows), Book(series), Ins(), Pol(), adjusted, backtest_n=16)
    assert out["stocks"] and out["as_of"] and out["backtest"]["models"]["picks_rule"]["days"] > 100
    assert out["backtest"]["periods"]["tickers"] == 16


def test_picks_board_without_an_overview_says_what_to_do():
    def cold():
        raise DataUnavailable("No Smart Money overview yet")
    with pytest.raises(DataUnavailable, match="overview"):
        picks_board(cold, Book({}), None, None, lambda t, y: [])


def test_a_failing_backtest_does_not_lose_the_picks():
    rows = [row(f"S{i}", 60 + i, 50) for i in range(6)]
    series = {f"S{i}": walk(0.001, 0.004, seed=i) for i in range(6)}

    def adjusted(t, years):
        raise DataUnavailable("blocked")
    out = picks_board(lambda: pick_overview(rows), Book(series), None, None, adjusted)
    assert out["stocks"] and out["backtest"] is None and out["backtest_error"]
