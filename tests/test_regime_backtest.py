"""Backtest walk-forward al semnalului de regim Markov: semn corect, fara
look-ahead (mostenit din walk_forward), metrici complete."""

import numpy as np

from markov import regime_backtest as rb


def test_markov_signal_long_in_uptrend_short_in_downtrend():
    up = 100 * 1.01 ** np.arange(80)
    down = 100 * 0.99 ** np.arange(80)
    assert rb.markov_signal(up, window=20, threshold=0.05) == 1.0
    assert rb.markov_signal(down, window=20, threshold=0.05) == -1.0


def test_markov_signal_zero_when_too_short():
    assert rb.markov_signal(np.array([100.0, 101.0, 102.0]), window=20) == 0.0


def test_walk_forward_markov_returns_full_metrics():
    rng = np.random.default_rng(0)
    prices = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, 600))
    out = rb.walk_forward_markov(prices, window=20, threshold=0.05)
    assert set(out) == {"sharpe", "max_drawdown", "net_return", "n_days"}
    assert out["n_days"] > 0
    assert out["max_drawdown"] <= 0.0                       # drawdown e <= 0


def test_walk_forward_markov_no_lookahead_safe_on_short_series():
    out = rb.walk_forward_markov(np.linspace(100, 110, 30), window=20)
    assert out["n_days"] == 0 and np.isnan(out["sharpe"])   # prea scurt -> gol, fara eroare
