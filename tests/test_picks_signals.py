import numpy as np
import pytest

from sensa.picks_signals import (composite, insider_features, momentum_features, politician_features, smart_money_features, zscores)


def series(daily, n=300, start=100.0):
    out, p = [], start
    for i in range(n):
        p *= 1 + (daily(i) if callable(daily) else daily)
        out.append(p)
    return out


def test_momentum_skips_the_last_month_and_flags_trend_vol_and_drawdown():
    up = momentum_features(series(0.001, 300))
    assert up["ret_12_1"] == pytest.approx(1.001 ** (252 - 21) - 1, rel=1e-6)
    assert up["trend"] == 1.0 and up["drawdown"] == pytest.approx(0.0, abs=1e-9) and up["vol"] == pytest.approx(0, abs=1e-6)
    crash = momentum_features(series(lambda i: 0.002 if i < 270 else -0.03, 300))
    assert crash["ret_1m"] < -0.3 and crash["drawdown"] < -0.3 and crash["ret_12_1"] > 0          # the last month is excluded from 12-1
    assert momentum_features(series(0.001, 100)) is None                                          # not enough history


def test_zscores_are_cross_sectional_winsorised_and_ignore_missing_values():
    z = zscores({"A": 1.0, "B": 2.0, "C": 3.0, "D": None})
    assert z["B"] == pytest.approx(0) and z["A"] < 0 < z["C"] and z["D"] is None
    big = zscores({**{f"S{i}": float(i) for i in range(20)}, "X": 1e9})
    assert max(v for v in big.values() if v is not None) <= 3.0 + 1e-9
    assert zscores({"A": 5.0, "B": 5.0}) == {"A": 0.0, "B": 0.0}


def test_smart_money_features_use_fund_count_change_and_active_flow_relative_to_value():
    f = smart_money_features({"holders": 60, "holders_prev": 50, "active_flow": 2e9, "value": 4e10, "new": 8, "exited": 2})
    assert f["holders_change"] == pytest.approx(0.2) and f["flow"] == pytest.approx(0.05) and f["net_new"] == 6
    assert smart_money_features({"holders": 5, "holders_prev": 0, "active_flow": 0, "value": 0, "new": 5, "exited": 0})["holders_change"] == 5.0


def test_insider_features_count_distinct_buyers_and_net_dollars_ignoring_plan_sales():
    trades = [{"symbol": "A", "owner": "Ann", "side": "buy", "value": 200000.0, "plan": False},
              {"symbol": "A", "owner": "Bob", "side": "buy", "value": 100000.0, "plan": False},
              {"symbol": "A", "owner": "Cy", "side": "sell", "value": 50000.0, "plan": False},
              {"symbol": "A", "owner": "Cy", "side": "sell", "value": 900000.0, "plan": True},     # scheduled 10b5-1 sale: not a view
              {"symbol": "B", "owner": "Dee", "side": "sell", "value": 1e6, "plan": False}]
    f = insider_features(trades)
    assert f["A"]["buyers"] == 2 and f["A"]["net"] == pytest.approx(250000.0) and f["B"]["net"] == -1e6 and f["B"]["buyers"] == 0


def test_politician_features_net_purchases_by_distinct_members():
    t = [{"ticker": "A", "type": "purchase", "member": "m1"}, {"ticker": "A", "type": "purchase", "member": "m2"},
         {"ticker": "A", "type": "sale", "member": "m3"}, {"ticker": "B", "type": "partial sale", "member": "m1"},
         {"ticker": "A", "type": "exchange", "member": "m1"}, {"ticker": "", "type": "purchase", "member": "m1"}]
    f = politician_features(t)
    assert f["A"] == {"buyers": 2, "sellers": 1, "net": 1} and f["B"]["net"] == -1 and "" not in f


def test_composite_renormalises_over_available_signals_and_needs_enough_of_them():
    w = {"momentum": 0.5, "smart": 0.3, "insider": 0.2}
    assert composite({"momentum": 2.0, "smart": 1.0, "insider": 0.0}, w) == pytest.approx(0.5 * 2 + 0.3 * 1)
    assert composite({"momentum": 2.0, "smart": None, "insider": None}, w, min_signals=2) is None
    assert composite({"momentum": 2.0, "smart": 1.0, "insider": None}, w, min_signals=2) == pytest.approx((0.5 * 2 + 0.3 * 1) / 0.8)
