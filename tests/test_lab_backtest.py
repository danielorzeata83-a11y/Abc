import numpy as np
import pandas as pd
import pytest

from sensa.lab_backtest import equal_weight, metrics, walk_forward


def frame(arr, start=20000):
    idx = [pd.Timestamp((start + i) * 86400, unit="s").strftime("%Y-%m-%d") for i in range(len(arr))]
    return pd.DataFrame(arr, index=idx, columns=[f"A{i}" for i in range(np.asarray(arr).shape[1])])


def test_metrics_of_a_constant_growth_series():
    r = pd.Series([0.01] * 252)
    m = metrics(r)
    assert m["ann_return"] == pytest.approx(1.01 ** 252 - 1) and m["ann_vol"] == pytest.approx(0, abs=1e-12) and m["max_drawdown"] == 0
    assert m["total_return"] == pytest.approx(1.01 ** 252 - 1)


def test_metrics_drawdown_sortino_cvar_and_calmar_on_a_known_series():
    r = pd.Series([0.10, -0.50, 0.20, 0.0])
    m = metrics(r)
    assert m["max_drawdown"] == pytest.approx(-0.5)                       # 1.1 -> 0.55
    assert m["cvar95"] == pytest.approx(0.5)                               # worst 5% of 4 observations = the single worst day
    assert np.isfinite(m["sortino"]) and m["calmar"] == pytest.approx(m["ann_return"] / 0.5)


def test_strategy_only_sees_data_strictly_before_the_rebalance_day():
    rng = np.random.default_rng(0)
    R = frame(rng.normal(0, 0.01, size=(120, 3)))
    seen = []

    def strat(train, w_prev):
        seen.append((len(train), train.index[-1]))
        return np.ones(3) / 3
    walk_forward(R, strat, window=50, every=20)
    firsts = [s[0] for s in seen]
    assert firsts == [50, 50, 50, 50] and seen[0][1] == R.index[49]       # first decision uses days 0..49 only, earns from day 50
    assert [s[1] for s in seen] == [R.index[49], R.index[69], R.index[89], R.index[109]]


def test_costs_are_charged_on_turnover_exactly():
    R = frame(np.zeros((90, 2)))
    flip = {"i": 0}

    def strat(train, w_prev):
        flip["i"] += 1
        return np.array([1.0, 0.0]) if flip["i"] % 2 else np.array([0.0, 1.0])
    res = walk_forward(R, strat, window=10, every=20, cost_bps=5)
    # decisions at 10, 30, 50, 70: first buys 100% of asset 0 (turnover 1 from cash), then three full flips (turnover 2)
    expected = (1 - 5e-4 * 1) * (1 - 5e-4 * 2) ** 3
    assert (1 + res["returns"]).prod() == pytest.approx(expected)
    assert res["turnover"] == [1.0, 2.0, 2.0, 2.0] and res["cost_total"] == pytest.approx(1 - expected, rel=1e-6)


def test_weights_drift_with_returns_between_rebalances_and_reported_returns_are_net():
    R2 = frame(np.vstack([np.zeros((5, 2)), [[0.10, 0.0]], np.zeros((20, 2))]))
    res = walk_forward(R2, lambda tr, wp: np.array([0.5, 0.5]), window=5, every=100, cost_bps=0)
    assert res["returns"].iloc[0] == pytest.approx(0.05)                   # 50% of the +10% asset
    assert res["daily_weights"].iloc[0].tolist() == pytest.approx([0.55 / 1.05, 0.5 / 1.05])       # drifted, end of day


def test_equal_weight_strategy_is_one_over_n():
    assert np.allclose(equal_weight(frame(np.zeros((3, 4))), None), 0.25)
