import numpy as np
import pytest

from sensa.regime_filter import current_regime, gate_backtest, regime_labels


def dates(n, start=20000):
    import pandas as pd
    return list(pd.bdate_range("2010-01-01", periods=n).strftime("%Y-%m-%d"))


def path(segments, vol=0.004, seed=0):
    """segments: [(days, daily drift)] -> price list"""
    rng = np.random.default_rng(seed)
    r = np.concatenate([rng.normal(d, vol, n) for n, d in segments])
    return list(100 * np.cumprod(1 + r))


def test_a_steady_uptrend_is_risk_on_with_the_reasons_spelled_out():
    c = path([(400, 0.0008)])
    reg = current_regime(c, dates(400))
    assert reg["label"] == "risk_on" and reg["spy"]["pct_vs_ma200"] > 0 and reg["spy"]["drawdown_pct"] > -5
    assert any("200-day" in r for r in reg["reasons"]) and reg["since"] <= reg["as_of"]


def test_a_sharp_fall_below_the_long_average_is_risk_off_and_the_start_of_the_episode_is_reported():
    c = path([(300, 0.001), (60, -0.012)])
    reg = current_regime(c, dates(360))
    assert reg["label"] == "risk_off" and reg["spy"]["drawdown_pct"] <= -10
    labels = regime_labels(c)
    first_bad = next(i for i, l in enumerate(labels) if l == "risk_off")
    assert reg["since"] == dates(360)[first_bad]


def test_not_enough_history_gives_no_regime():
    assert current_regime(path([(100, 0.001)]), dates(100)) is None


def test_trend_gate_backtest_reports_gate_vs_buy_and_hold_and_an_honest_verdict():
    crash = path([(500, 0.0008), (120, -0.010), (400, 0.0010)], vol=0.003, seed=1)
    r = gate_backtest(crash, dates(len(crash)))
    assert r["gate"]["max_drawdown"] > r["buy_hold"]["max_drawdown"]                   # stepping aside in the fall cut the loss
    assert 0 < r["time_in_market_pct"] < 100 and r["window"] == 200 and r["days"] > 500
    assert r["verdict"] in ("helped", "mixed", "did_not_help") and "past" in r["verdict_text"].lower()


def test_in_a_choppy_market_the_gate_can_hurt_and_the_verdict_says_so():
    rng = np.random.default_rng(5)
    chop = list(100 * np.cumprod(1 + rng.normal(0.0002, 0.012, 1500)))
    r = gate_backtest(chop, dates(1500))
    assert r["verdict"] in ("helped", "mixed", "did_not_help")
    assert r["gate"]["sharpe"] is not None and r["buy_hold"]["sharpe"] is not None
    if r["verdict"] != "helped":
        assert "did not" in r["verdict_text"].lower() or "mixed" in r["verdict_text"].lower() or "no clear" in r["verdict_text"].lower()
