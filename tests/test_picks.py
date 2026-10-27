import numpy as np
import pytest

from sensa.picks import ETF_CATALOG, build_picks


class Book:
    def __init__(self, series):
        self.s = series
        self.warmed = []

    def warm(self, tickers):
        self.warmed.extend(tickers)

    def closes(self, t):
        c = self.s.get(t.upper())
        if c is None:
            return None
        import pandas as pd
        return (list(pd.bdate_range(end="2026-10-23", periods=len(c)).strftime("%Y-%m-%d")), c)

    def last(self, t):
        c = self.s.get(t.upper())
        return ("2026-10-23", c[-1]) if c else None

    def on_or_before(self, t, day):
        h = self.closes(t)
        rows = [(d, x) for d, x in zip(*h) if d <= day] if h else []
        return rows[-1] if rows else None

    def on_or_after(self, t, day):
        h = self.closes(t)
        rows = [(d, x) for d, x in zip(*h) if d >= day] if h else []
        return rows[0] if rows else None


def walk(drift, vol=0.01, n=320, seed=0, start=50.0):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    return list(start * np.cumprod(1 + r))


def row(t, holders=50, prev=50, flow=0.0, value=1e10, issuer=None, kind="stock", new=0, exited=0):
    return {"ticker": t, "issuer": issuer or t + " CORP", "kind": kind, "holders": holders, "holders_prev": prev, "active_flow": flow,
            "value": value, "new": new, "exited": exited, "gone": False, "new_listing": False}


def overview(rows):
    return {"stocks": rows, "quarter": "Q2 2026"}


def run(rows, series, insiders=(), pols=(), **kw):
    return build_picks(overview(rows), Book(series), list(insiders), list(pols), **kw)


def test_strong_momentum_and_fund_buying_rank_above_weak_names_and_downtrends_are_excluded():
    rows = [row("WIN", 80, 60, flow=2e9), row("MID", 60, 58), row("LAG", 40, 55, flow=-1e9), row("DWN", 70, 70)]
    base = walk(0.0015, vol=0.002, seed=4, n=250)
    series = {"WIN": walk(0.0020, vol=0.002, seed=1), "MID": walk(0.0006, vol=0.002, seed=2), "LAG": walk(0.0004, vol=0.002, seed=3),
              "DWN": base + list(base[-1] * np.cumprod(1 - np.full(70, 0.02)))}
    res = run(rows, series, top_n=3)
    names = [p["ticker"] for p in res["stocks"]]
    assert names == ["WIN", "MID", "LAG"] and res["skipped"]["downtrend"] == 1       # DWN fell below its 200-day average
    assert res["stocks"][0]["score"] > res["stocks"][-1]["score"] and res["stocks"][0]["rank"] == 1


def test_insider_buying_lifts_an_otherwise_identical_stock():
    rows = [row("AAA", 60, 60), row("BBB", 60, 60), row("CCC", 60, 60)]
    series = {"AAA": walk(0.001, seed=5), "BBB": walk(0.001, seed=5), "CCC": walk(0.0009, seed=9)}
    series["BBB"] = list(series["AAA"])
    trades = [{"symbol": "AAA", "owner": o, "side": "buy", "value": 300000.0, "plan": False} for o in ("a", "b", "c")]
    res = run(rows, series, insiders=trades, dedupe_corr=2.0, top_n=3)
    order = [p["ticker"] for p in res["stocks"]]
    assert order.index("AAA") < order.index("BBB")
    assert any("insider" in r.lower() for r in res["stocks"][order.index("AAA")]["reasons"])


def test_share_classes_and_near_duplicates_are_picked_once_keeping_the_better_score():
    rows = [row("GOOGL", 80, 70, issuer="ALPHABET INC"), row("GOOG", 78, 70, issuer="ALPHABET INC"), row("OTH", 60, 60)]
    base = walk(0.002, seed=11)
    series = {"GOOGL": base, "GOOG": [x * 0.99 for x in base], "OTH": walk(0.001, seed=12)}
    res = run(rows, series, top_n=3)
    assert [p["ticker"] for p in res["stocks"]].count("GOOGL") + [p["ticker"] for p in res["stocks"]].count("GOOG") == 1
    corr_dup = run([row("AAA", 70, 60), row("BBB", 69, 60, issuer="OTHER LTD")], {"AAA": base, "BBB": [x * 1.01 for x in base]}, top_n=2)
    assert len(corr_dup["stocks"]) == 1 and any("duplicate" in s.lower() or "same" in s.lower() for s in corr_dup["skipped_notes"])


def test_weights_sum_to_one_follow_inverse_volatility_and_respect_the_cap():
    rows = [row(t, 60 + i, 55) for i, t in enumerate(["A1", "A2", "A3", "A4", "A5"])]
    series = {"A1": walk(0.0015, 0.004, seed=21), "A2": walk(0.0015, 0.010, seed=22), "A3": walk(0.0015, 0.020, seed=23),
              "A4": walk(0.0015, 0.012, seed=24), "A5": walk(0.0015, 0.015, seed=25)}
    res = run(rows, series, top_n=5, max_weight=0.3)
    w = {p["ticker"]: p["weight"] for p in res["stocks"]}
    assert sum(w.values()) == pytest.approx(1.0) and max(w.values()) <= 0.3 + 1e-9 and w["A1"] > w["A3"]


def test_short_histories_and_cheap_stocks_are_skipped_and_counted():
    rows = [row("OK", 70, 60), row("NEW", 70, 60), row("PENNY", 70, 60)]
    series = {"OK": walk(0.001, seed=31), "NEW": walk(0.001, seed=32, n=100), "PENNY": walk(0.001, seed=33, start=0.5)}
    res = run(rows, series, top_n=5, min_price=5.0)
    assert [p["ticker"] for p in res["stocks"]] == ["OK"] and res["skipped"]["no_history"] == 1 and res["skipped"]["low_price"] == 1


def test_reasons_quote_the_numbers_behind_each_signal():
    rows = [row("WIN", 80, 60, flow=2e9, value=4e10, new=9, exited=2), row("X", 50, 50)]
    trades = [{"symbol": "WIN", "owner": "o1", "side": "buy", "value": 250000.0, "plan": False}]
    pols = [{"ticker": "WIN", "type": "purchase", "member": "m1"}]
    res = run(rows, {"WIN": walk(0.002, seed=41), "X": walk(0.0004, seed=42)}, insiders=trades, pols=pols, top_n=2)
    text = " | ".join(res["stocks"][0]["reasons"])
    assert res["stocks"][0]["ticker"] == "WIN" and "80 of the top funds" in text and "+20" in text
    assert "insider" in text.lower() and "House" in text and "200-day" in text


def etf_rows():
    return [row("QQQ", 90, 85, kind="etf", issuer="INVESCO QQQ TR"), row("TQQQ", 30, 20, kind="etf", issuer="PROSHARES ULTRAPRO QQQ"),
            row("SQQQ", 25, 20, kind="etf", issuer="PROSHARES ULTRAPRO SHORT QQQ"), row("AAA", 60, 60)]


def test_etfs_exclude_leveraged_and_inverse_funds_and_cap_each_category():
    series = {t: walk(0.0008 + 0.0001 * i, 0.008, seed=50 + i) for i, t in enumerate(sorted(ETF_CATALOG))}
    series.update({"QQQ": walk(0.0015, 0.01, seed=99), "TQQQ": walk(0.004, 0.03, seed=98), "SQQQ": walk(0.004, 0.03, seed=97), "AAA": walk(0.001, seed=96)})
    res = run(etf_rows(), series, top_n=10)
    t = [p["ticker"] for p in res["etfs"]]
    assert "TQQQ" not in t and "SQQQ" not in t and len(t) <= 10
    cats = [p["category"] for p in res["etfs"]]
    assert all(cats.count(c) <= 3 for c in set(cats))
    assert all(p["weight"] > 0 for p in res["etfs"]) and sum(p["weight"] for p in res["etfs"]) == pytest.approx(1.0)


def test_identical_index_funds_are_listed_once():
    series = {t: walk(0.0007, 0.008, seed=70 + i) for i, t in enumerate(sorted(ETF_CATALOG))}
    base = walk(0.002, 0.009, seed=5)
    series.update({"SPY": base, "VOO": [x * 1.001 for x in base], "IVV": [x * 0.999 for x in base]})
    res = run([row("AAA", 60, 60)], {**series, "AAA": walk(0.001, seed=1)}, top_n=10)
    assert len({"SPY", "VOO", "IVV"} & {p["ticker"] for p in res["etfs"]}) == 1


def test_method_and_notes_are_part_of_the_output():
    res = run([row("A", 60, 55), row("B", 61, 55)], {"A": walk(0.001, seed=1), "B": walk(0.001, seed=2)}, top_n=2)
    assert res["method"]["stock_weights"]["smart"] > 0 and "not investment advice" in res["notice"].lower() and res["as_of"] == "2026-10-23"


def test_trust_names_are_replaced_by_the_ticker_and_very_extended_stocks_carry_a_caution():
    rows = [row("HOT", 80, 70, issuer="HOT CORP"), row("ZZXA", 70, 60, kind="etf", issuer="SPDR SERIES TRUST"), row("ZZXB", 60, 50, kind="etf", issuer="SCHWAB STRATEGIC TR")]
    series = {t: walk(0.0007, 0.008, seed=60 + i) for i, t in enumerate(sorted(ETF_CATALOG))}
    series["HOT"] = [50.0 * 1.012 ** i for i in range(320)]                           # +~4000% in a year: wildly extended
    series["ZZXA"], series["ZZXB"] = walk(0.002, 0.009, seed=1), walk(0.0018, 0.009, seed=2)
    res = run(rows, series, top_n=60, max_per_category=60)                          # list everything: the test is about the labels
    assert any("extended" in r.lower() and "pullback" in r.lower() for r in res["stocks"][0]["reasons"])
    names = {p["ticker"]: p["name"] for p in res["etfs"]}
    assert names.get("ZZXA") == "ZZXA (ETF held by funds)" and names.get("ZZXB") == "ZZXB (ETF held by funds)"


def test_output_carries_the_prices_of_the_scored_pool_for_the_track_record():
    res = run([row("A", 60, 55), row("B", 61, 55)], {"A": walk(0.001, 0.002, seed=1), "B": walk(0.0012, 0.002, seed=2)}, top_n=2)
    assert set(res["pool_prices"]) == {"stocks", "etfs"} and set(res["pool_prices"]["stocks"]) == {"A", "B"}
    assert all(isinstance(v, float) for v in res["pool_prices"]["stocks"].values())
