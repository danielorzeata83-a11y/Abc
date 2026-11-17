"""Scorerul comun de pozitii: cost reduce net-ul, metrici complete, p in (0,1]."""

import numpy as np

from markov.posscore import score_positions


def test_metrics_present_and_cost_reduces_net():
    rng = np.random.default_rng(0)
    fwd = rng.normal(0.0005, 0.01, 300)
    pos = np.ones(300)                       # long mereu
    free = score_positions(pos, fwd, cost=0.0, n_perm=100)
    assert set(free) == {"gross_return", "net_return", "sharpe", "max_drawdown",
                         "n_trades", "n_days", "p_value"}
    assert np.isclose(free["gross_return"], free["net_return"])   # cost 0
    assert 0.0 < free["p_value"] <= 1.0
    assert free["max_drawdown"] <= 0.0


def test_turnover_drives_cost():
    fwd = np.full(10, 0.01)
    flip = np.array([1.0, 0, 1, 0, 1, 0, 1, 0, 1, 0])   # turnover la fiecare bara
    r = score_positions(flip, fwd, cost=0.01, n_perm=10)
    assert r["n_trades"] == 10               # intrarea initiala + 9 schimbari
    assert r["net_return"] < r["gross_return"]
