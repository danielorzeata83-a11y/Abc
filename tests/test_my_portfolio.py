import json

import numpy as np
import pytest

from sensa.my_portfolio import MyPortfolio, analyze, clean_positions


def series(drift, vol, n=300, seed=0, start=100.0):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    return list(start * np.cumprod(1 + r))


class Book:
    def __init__(self, s):
        self.s, self.warmed = s, []

    def warm(self, t):
        self.warmed.extend(t)

    def closes(self, t):
        c = self.s.get(t.upper())
        if c is None:
            return None
        import pandas as pd
        return (list(pd.bdate_range(end="2026-10-23", periods=len(c)).strftime("%Y-%m-%d")), c)

    def last(self, t):
        c = self.s.get(t.upper())
        return ("2026-10-23", c[-1]) if c else None


BOOK = {"AAA": series(0.0008, 0.010, seed=1), "BBB": series(0.0002, 0.012, seed=2), "CCC": series(0.0004, 0.015, seed=3), "SPY": series(0.0004, 0.008, seed=4)}
BOOK["DUP"] = [x * 1.02 for x in BOOK["AAA"]]


def pos(*rows):
    return [{"ticker": t, "shares": s, "cost": c} for t, s, c in rows]


def test_positions_are_validated_and_cleaned():
    out = clean_positions([{"ticker": " aapl ", "shares": "10", "cost": "150.5"}, {"ticker": "AAPL", "shares": 5, "cost": 160}, {"ticker": "msft", "shares": 3, "cost": None}])
    assert out == [{"ticker": "AAPL", "shares": 15.0, "cost": pytest.approx((10 * 150.5 + 5 * 160) / 15)}, {"ticker": "MSFT", "shares": 3.0, "cost": None}]
    for bad in ([{"ticker": "BAD/X", "shares": 1}], [{"ticker": "A", "shares": 0}], [{"ticker": "A", "shares": -2}], [{"ticker": "A", "shares": "x"}], "no", [{"ticker": "A", "shares": 1, "cost": -5}]):
        with pytest.raises(ValueError):
            clean_positions(bad)
    with pytest.raises(ValueError):
        clean_positions([{"ticker": f"T{i}", "shares": 1} for i in range(101)])


def test_values_weights_and_profit_use_the_last_close_and_skip_unpriced_tickers():
    a = analyze(pos(("AAA", 10, 100.0), ("BBB", 20, 50.0), ("NOPE", 5, 10.0)), Book(BOOK))
    rows = {r["ticker"]: r for r in a["positions"]}
    last_a, last_b = BOOK["AAA"][-1], BOOK["BBB"][-1]
    assert rows["AAA"]["value"] == pytest.approx(10 * last_a) and rows["AAA"]["pnl"] == pytest.approx(10 * (last_a - 100.0))
    assert rows["AAA"]["pnl_pct"] == pytest.approx((last_a / 100.0 - 1) * 100) and rows["NOPE"]["value"] is None and "no price" in rows["NOPE"]["note"].lower()
    assert a["totals"]["value"] == pytest.approx(10 * last_a + 20 * last_b) and sum(r["weight"] for r in a["positions"] if r["weight"]) == pytest.approx(1.0)


def test_risk_metrics_concentration_and_correlated_pairs():
    a = analyze(pos(("AAA", 10, None), ("DUP", 10, None), ("CCC", 5, None)), Book(BOOK))
    r = a["risk"]
    assert r["vol_pct"] > 0 and r["max_drawdown_pct"] <= 0 and r["cvar95_pct"] > 0 and r["beta"] is not None and 0 < r["effective_n"] < 3
    assert {tuple(sorted((p["a"], p["b"]))) for p in a["correlated_pairs"]} == {("AAA", "DUP")}
    assert a["risk"]["top3_weight_pct"] == pytest.approx(100.0)


def test_warnings_for_concentration_drawdown_from_cost_and_broken_trend():
    book = {**BOOK, "BRK": series(0.0006, 0.01, seed=7, n=250) + list(np.array(series(0.0006, 0.01, seed=7, n=250))[-1] * np.cumprod(1 - np.full(50, 0.02)))}
    a = analyze(pos(("AAA", 100, 50.0), ("BRK", 1, 500.0), ("BBB", 1, 1.0)), Book(book))
    text = " | ".join(w["text"] for w in a["warnings"])
    assert "AAA" in text and "of your portfolio" in text                      # one position dominates
    assert "BRK" in text and "200-day" in text                                 # fell below its long-term average
    assert any(w["ticker"] == "BRK" and "below your cost" in w["text"] for w in a["warnings"])


def test_smart_money_context_for_each_holding():
    ov = {"stocks": [{"ticker": "AAA", "holders": 70, "holders_prev": 80, "active_flow": -2e9, "value": 4e10, "kind": "stock"}]}
    trades = [{"symbol": "AAA", "owner": "x", "side": "sell", "value": 3e6, "plan": False, "date": "2026-10-01"}]
    a = analyze(pos(("AAA", 10, None), ("BBB", 10, None)), Book(BOOK), overview=ov, insider_trades=trades, picks={"stocks": [{"ticker": "BBB", "rank": 4}], "etfs": []})
    rows = {r["ticker"]: r for r in a["positions"]}
    assert rows["AAA"]["funds"] == {"holders": 70, "change": -10, "flow": -2e9} and rows["BBB"]["pick_rank"] == 4 and rows["AAA"]["pick_rank"] is None
    text = " | ".join(w["text"] for w in a["warnings"])
    assert "funds" in text and "sold" in text and "insiders" in text


def test_alternatives_show_equal_inverse_vol_and_a_risk_aware_mix_with_their_volatility():
    a = analyze(pos(("AAA", 10, None), ("BBB", 10, None), ("CCC", 10, None)), Book(BOOK))
    alt = {x["name"]: x for x in a["alternatives"]}
    assert set(alt) == {"current", "equal", "inverse_vol", "optimized"}
    for x in alt.values():
        assert sum(x["weights"].values()) == pytest.approx(1.0) and x["vol_pct"] > 0
    assert alt["inverse_vol"]["vol_pct"] <= alt["equal"]["vol_pct"] + 1e-9
    assert all(abs(t["delta_pct"]) >= 0 for t in a["trades_to_optimized"])


def test_empty_or_unpriced_portfolio_is_explained():
    assert analyze([], Book(BOOK))["message"]
    assert analyze(pos(("NOPE", 1, None)), Book(BOOK))["message"]


def test_service_saves_loads_and_exposes_alerts(tmp_path):
    path = str(tmp_path / "p.json")
    svc = MyPortfolio(path, Book(BOOK))
    svc.set([{"ticker": "aaa", "shares": 100, "cost": 10}, {"ticker": "bbb", "shares": 1, "cost": 1}])
    assert [p["ticker"] for p in MyPortfolio(path, Book(BOOK)).positions()] == ["AAA", "BBB"]
    a = svc.get()
    assert a["positions"] and "SPY" in svc.prices.warmed
    al = svc.alerts()
    assert al["section"] == "portfolio" and al["items"] and all({"key", "text", "severity"} <= i.keys() for i in al["items"])
    assert MyPortfolio(None, Book(BOOK)).alerts() is None
