"""Metrici de trader: segmentare corecta a tranzactiilor, win-rate,
profit-factor si expectancy pe cazuri cunoscute."""

import numpy as np

from markov.tradestats import trade_stats


def test_two_winning_trades_counted():
    pos = np.array([1.0, 1, 0, 1, 0])
    fwd = np.array([0.1, 0.1, -0.5, 0.2, -0.5])   # detine doar la pos>0
    s = trade_stats(pos, fwd, cost=0.0)
    assert s["n_trades"] == 2                      # doua runuri de pozitie
    assert s["win_rate"] == 1.0
    assert s["profit_factor"] == float("inf")      # nicio pierdere
    assert s["expectancy"] > 0


def test_mixed_win_and_loss():
    pos = np.array([1.0, 0, 1, 0])
    fwd = np.array([-0.3, 0.0, 0.1, 0.0])
    s = trade_stats(pos, fwd, cost=0.0)
    assert s["n_trades"] == 2
    assert s["win_rate"] == 0.5
    assert np.isclose(s["profit_factor"], 0.1 / 0.3, atol=1e-6)
    assert s["max_drawdown"] <= 0.0


def test_no_trades_is_safe():
    s = trade_stats(np.zeros(10), np.full(10, 0.01))
    assert s["n_trades"] == 0 and np.isnan(s["win_rate"])
