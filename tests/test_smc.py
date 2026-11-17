"""Harness SMC (Smart Money Concepts) — testeaza ca primitivele sunt CAUZALE
(fara repaint) si ca backtestul produce metrici net de costuri + p-value.

Scopul harness-ului: sa vedem onest daca o regula SMC simpla (BOS + retest FVG)
are vreun edge cand e codificata fara look-ahead. NU consiliere de investitii.
"""

import numpy as np

from markov import smc
from markov.intraday.bars import Bars


def _bars_from_close(close, spread=0.5):
    close = np.asarray(close, dtype=float)
    idx = np.arange(len(close)).astype("datetime64[D]")
    return Bars(idx, close, close + spread, close - spread, close,
                np.full(len(close), 1e6))


def test_swing_high_known_only_after_k_bars():
    # varf clar la indexul 5; cu k=2 e CONFIRMAT abia la t=7 (are nevoie de
    # 2 bare in viitor) -> inainte de t=7 nu poate fi cunoscut (fara repaint).
    high = np.array([1, 2, 3, 4, 5, 10, 5, 4, 3, 2, 1], dtype=float)
    low = high - 1.0
    sh, sl = smc.swing_points(high, low, k=2)
    assert np.isnan(sh[6])          # inca neconfirmat la t=6
    assert sh[7] == 10.0            # confirmat la t = varf + k
    assert sh[5] == sh[5] or True   # (nan la varf insusi)
    assert np.isnan(sh[5])


def test_fvg_detects_injected_bullish_gap_and_none_when_flat():
    # gol bullish la i=2: low[2] > high[0]. Bara 0 high=2, bara 2 low=5 -> gol (2,5).
    high = np.array([2.0, 6.0, 9.0, 9.0])
    low = np.array([1.0, 3.0, 5.0, 7.0])
    fvg = smc.fair_value_gaps(high, low)
    bull = fvg["bullish"]
    assert any(i == 2 and bot == 2.0 and top == 5.0 for (i, bot, top) in bull)
    # serie plata, fara goluri
    flat_h = np.full(6, 3.0)
    flat_l = np.full(6, 1.0)
    z = smc.fair_value_gaps(flat_h, flat_l)
    assert z["bullish"] == [] and z["bearish"] == []


def _staircase_uptrend(n_cycles=16, up=1.2, dip=1.6, x0=100.0):
    close, x = [], x0
    for _ in range(n_cycles):
        for _ in range(4):
            x += up
            close.append(x)
        x -= dip
        close.append(x)
    return np.array(close)


def test_positions_are_ternary_and_flat_series_stays_flat():
    pos = smc.smc_positions(_bars_from_close(_staircase_uptrend(), spread=0.2))
    assert set(np.unique(pos)).issubset({-1.0, 0.0, 1.0})
    flat = smc.smc_positions(_bars_from_close(np.full(60, 100.0)))
    assert np.all(flat == 0.0)             # fara structura -> niciun BOS, plat


def test_uptrend_produces_at_least_one_long():
    pos = smc.smc_positions(_bars_from_close(_staircase_uptrend(), spread=0.2))
    assert (pos > 0).sum() > 0             # regula prinde macar un long in trend


def test_positions_have_no_lookahead_prefix_stable():
    # Pozitiile pe un prefix trebuie sa coincida cu cele pe seria completa
    # (pana langa coada, unde swing-urile inca nu-s confirmate) -> fara repaint.
    close = _staircase_uptrend()
    full = smc.smc_positions(_bars_from_close(close, spread=0.2))
    pre = smc.smc_positions(_bars_from_close(close[:60], spread=0.2))
    np.testing.assert_array_equal(full[:55], pre[:55])


def test_backtest_reports_metrics_and_cost_reduces_net():
    bars = _bars_from_close(_staircase_uptrend(), spread=0.2)
    free = smc.backtest_smc(bars, cost=0.0, n_perm=200, seed=0)
    assert set(free) == {"gross_return", "net_return", "sharpe", "max_drawdown",
                         "n_trades", "n_days", "p_value"}
    assert free["max_drawdown"] <= 0.0
    assert 0.0 < free["p_value"] <= 1.0
    assert np.isclose(free["gross_return"], free["net_return"])   # cost 0 -> egale
    if free["n_trades"] > 0:
        costly = smc.backtest_smc(bars, cost=0.005, n_perm=10, seed=0)
        assert costly["net_return"] < free["net_return"]          # costul musca net
