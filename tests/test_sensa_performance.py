import pytest

from sensa.performance import fund_performance, insider_buy_performance, insider_holdings, member_leaderboard


class Prices:
    """series: {ticker: [(date, close)]}"""
    def __init__(self, series):
        self.s = series

    def _rows(self, t):
        return self.s.get(t.upper(), [])

    def last(self, t):
        r = self._rows(t)
        return r[-1] if r else None

    def on_or_before(self, t, day):
        c = [x for x in self._rows(t) if x[0] <= day]
        return c[-1] if c else None

    def on_or_after(self, t, day):
        c = [x for x in self._rows(t) if x[0] >= day]
        return c[0] if c else None


SERIES = {"AAA": [("2026-06-30", 10.0), ("2026-08-14", 12.0), ("2026-10-23", 15.0)],
          "BBB": [("2026-06-30", 20.0), ("2026-08-14", 20.0), ("2026-10-23", 10.0)],
          "SPY": [("2026-06-30", 100.0), ("2026-08-14", 105.0), ("2026-10-23", 110.0)]}
TICKERS = {"c1": "AAA", "c2": "BBB", "c3": None, "c4": "ZZZ"}


def test_fund_return_since_period_end_and_since_filing_use_a_buy_and_hold_basket():
    pos = [{"cusip": "c1", "issuer": "A", "shares": 100, "value": 1000.0}, {"cusip": "c2", "issuer": "B", "shares": 50, "value": 1000.0},
           {"cusip": "c3", "issuer": "UNMAPPED", "shares": 10, "value": 500.0}, {"cusip": "c4", "issuer": "NOPRICE", "shares": 10, "value": 500.0}]
    r = fund_performance(pos, TICKERS.get, Prices(SERIES), "2026-06-30", "2026-08-14")
    assert r["value_period_end"] == 2000.0 and r["value_now"] == 100 * 15 + 50 * 10 == 2000.0
    assert r["return_since_period_pct"] == 0.0
    assert r["return_since_filing_pct"] == round((2000 / (100 * 12 + 50 * 20) - 1) * 100, 2)      # -9.09
    assert r["spy_since_period_pct"] == 10.0 and r["spy_since_filing_pct"] == round((110 / 105 - 1) * 100, 2)
    assert r["covered_pct"] == round(2000 / 3000 * 100, 2) and r["covered_positions"] == 2 and r["positions_total"] == 4
    assert r["as_of"] == "2026-10-23"
    assert [x["ticker"] for x in r["rows"]] == ["AAA", "BBB"] and r["rows"][0]["change_since_filing_pct"] == 25.0


def test_fund_with_nothing_priced_has_no_returns():
    r = fund_performance([{"cusip": "c3", "issuer": "X", "shares": 1, "value": 1.0}], TICKERS.get, Prices(SERIES), "2026-06-30", "2026-08-14")
    assert r["covered_positions"] == 0 and r["return_since_filing_pct"] is None and r["rows"] == []


def trade(member, ticker, kind, date, filed, value=1000.0):
    return {"member": member, "ticker": ticker, "type": kind, "date": date, "filed": filed, "value": value}


def test_member_leaderboard_scores_purchases_from_the_trade_day_and_from_the_filing_day_against_spy():
    trades = [trade("Ann", "AAA", "purchase", "2026-06-30", "2026-08-14", 3000.0),
              trade("Ann", "BBB", "purchase", "2026-06-30", "2026-08-14", 1000.0),
              trade("Ann", "AAA", "sale", "2026-06-30", "2026-08-14", 500.0),
              trade("Bob", "BBB", "purchase", "2026-06-30", "2026-08-14"),
              trade("Cy", "NONE", "purchase", "2026-06-30", "2026-08-14")]
    rows = member_leaderboard(trades, Prices(SERIES), min_buys=1)
    by = {r["member"]: r for r in rows}
    ann = by["Ann"]
    assert ann["buys"] == 2 and ann["sells"] == 1 and ann["est_volume"] == 4500.0
    assert ann["return_since_trade_pct"] == round((3000 * 0.5 + 1000 * -0.5) / 4000 * 100, 2) == 25.0       # AAA +50%, BBB -50%
    assert ann["spy_since_trade_pct"] == 10.0 and ann["alpha_since_trade_pct"] == 15.0
    assert ann["return_since_filing_pct"] == round((3000 * 0.25 + 1000 * -0.5) / 4000 * 100, 2)             # AAA +25% from 12, BBB -50%
    assert by["Bob"]["return_since_trade_pct"] == -50.0 and "Cy" not in by          # nothing priced: not ranked
    assert [r["member"] for r in rows][0] == "Ann"                                   # best since filing first


def test_member_leaderboard_needs_the_minimum_number_of_priced_buys():
    trades = [trade("Ann", "AAA", "purchase", "2026-06-30", "2026-08-14")]
    assert member_leaderboard(trades, Prices(SERIES), min_buys=2) == []


def itrade(owner, sym, side, date, price, shares=100.0, owned=None):
    return {"owner": owner, "symbol": sym, "side": side, "date": date, "price": price, "shares": shares, "value": price * shares,
            "owned_after": owned, "role": "CEO", "issuer": sym}


def test_insider_holdings_take_the_latest_reported_balance_and_value_it_today():
    trades = [itrade("Ann", "AAA", "buy", "2026-07-01", 10.0, owned=1000.0), itrade("Ann", "AAA", "buy", "2026-09-01", 12.0, owned=1500.0),
              itrade("Bob", "AAA", "sell", "2026-09-01", 13.0, owned=None), itrade("Cy", "BBB", "buy", "2026-09-01", 20.0, owned=200.0)]
    h = {(r["owner"], r["symbol"]): r for r in insider_holdings(trades, Prices(SERIES))}
    assert h[("Ann", "AAA")]["shares"] == 1500.0 and h[("Ann", "AAA")]["value"] == 1500 * 15.0 and h[("Ann", "AAA")]["as_of_trade"] == "2026-09-01"
    assert ("Bob", "AAA") not in h                                           # no balance reported
    assert h[("Cy", "BBB")]["avg_buy_price"] == 20.0 and h[("Cy", "BBB")]["buy_return_pct"] == -50.0


def test_insider_buy_performance_averages_open_market_buys_against_spy():
    trades = [itrade("Ann", "AAA", "buy", "2026-06-30", 10.0), itrade("Cy", "BBB", "buy", "2026-06-30", 20.0),
              itrade("Bob", "AAA", "sell", "2026-06-30", 10.0)]
    r = insider_buy_performance(trades, Prices(SERIES))
    assert r["n"] == 2 and r["avg_return_pct"] == 0.0                       # +50% and -50%
    assert r["spy_pct"] == 10.0 and r["win_rate_pct"] == 50.0
    assert r["best"][0]["symbol"] == "AAA" and r["worst"][0]["symbol"] == "BBB"


def test_insider_returns_use_the_same_split_adjusted_price_series_for_entry_and_exit():
    # the reported price (40) is pre-split; the adjusted close on that day is 10
    trades = [itrade("Ann", "AAA", "buy", "2026-06-30", 40.0)]
    r = insider_buy_performance(trades, Prices(SERIES))
    assert r["best"][0]["return_pct"] == 50.0 and r["median_return_pct"] == 50.0
