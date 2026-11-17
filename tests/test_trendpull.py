"""Sistem trend-pullback: primitivele sunt cauzale, regula intra long doar in
trend confirmat la retest, e plata in downtrend, fara look-ahead, iar selectia
multiplicatorului ATR raporteaza OUT-OF-SAMPLE."""

import numpy as np

from markov import trendpull as tp
from markov.intraday.bars import Bars


def _bars(close, band=1.0):
    close = np.asarray(close, dtype=float)
    idx = np.arange(len(close)).astype("datetime64[D]")
    return Bars(idx, close, close + band, close - band, close,
                np.full(len(close), 1e6))


def _uptrend_with_pullbacks(n=220, drift=0.25, amp=10.0, period=6.0, base=100.0):
    t = np.arange(n)
    return base + drift * t + amp * np.sin(t / period)


def test_ma_and_atr_are_causal():
    close = np.arange(1, 61, dtype=float)
    m = tp.ma(close, 50)
    assert np.isnan(m[48]) and not np.isnan(m[49])      # NaN pana la fereastra
    a = tp.atr(close + 1, close - 1, close, 22)
    assert np.isnan(a[20]) and a[21] > 0


def test_trend_up_true_rising_false_falling():
    rise = np.arange(1, 101, dtype=float)
    fall = rise[::-1].copy()
    assert tp.trend_up(rise, tp.ma(rise, 50), 10)[-1]
    assert not tp.trend_up(fall, tp.ma(fall, 50), 10)[-1]


def test_positions_long_only_and_enters_in_uptrend():
    pos = tp.trendpull_positions(_bars(_uptrend_with_pullbacks()))
    assert set(np.unique(pos)).issubset({0.0, 1.0})     # long-only
    assert (pos > 0).sum() > 0                           # prinde macar un retest


def test_no_long_in_downtrend():
    down = 200.0 - 0.3 * np.arange(220)                   # declin curat, monoton
    pos = tp.trendpull_positions(_bars(down))
    assert (pos > 0).sum() == 0                           # niciodata long in jos


def test_positions_prefix_stable_no_lookahead():
    close = _uptrend_with_pullbacks()
    full = tp.trendpull_positions(_bars(close))
    pre = tp.trendpull_positions(_bars(close[:180]))
    np.testing.assert_array_equal(full[:175], pre[:175])


def test_walk_forward_select_reports_oos_and_picks_from_grid():
    bars = _bars(_uptrend_with_pullbacks())
    res = tp.walk_forward_select(bars, mults=(2.0, 3.0, 4.0), split=0.5,
                                 n_perm=50)
    assert res["chosen_mult"] in (2.0, 3.0, 4.0)
    assert set(res["oos"]) >= {"net_return", "sharpe", "p_value"}
    assert 0.0 < res["oos"]["p_value"] <= 1.0
