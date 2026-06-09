"""Sistem buy-the-dip: long-only, intra dupa o cadere destul de mare, e plat
daca pretul nu cade, fara look-ahead (prefix-stabil)."""

import numpy as np

from markov import dipbuy
from markov.intraday.bars import Bars


def _bars(close, band=1.0):
    close = np.asarray(close, dtype=float)
    idx = np.arange(len(close)).astype("datetime64[D]")
    return Bars(idx, close, close + band, close - band, close,
                np.full(len(close), 1e6))


def _crash_then_recover():
    up = np.linspace(50, 100, 60)
    crash = np.linspace(100, 62, 15)        # -38% de la varf
    rec = np.linspace(62, 95, 40)
    return np.concatenate([up, crash, rec])


def test_drawdown_is_nonpositive_and_zero_at_new_high():
    close = np.arange(1, 101, dtype=float)  # mereu maxim nou
    dd = dipbuy.drawdown(close, lookback=20)
    fin = dd[~np.isnan(dd)]
    assert np.all(fin <= 1e-9) and np.isclose(fin[-1], 0.0)


def test_enters_long_after_big_drop():
    pos = dipbuy.dipbuy_positions(_bars(_crash_then_recover()),
                                  dip=0.2, lookback=20, exit_ma=10)
    assert set(np.unique(pos)).issubset({0.0, 1.0})
    assert (pos > 0).sum() > 0               # a cumparat dipul


def test_no_entry_when_only_rising():
    pos = dipbuy.dipbuy_positions(_bars(np.linspace(50, 150, 200)),
                                  dip=0.2, lookback=20, exit_ma=10)
    assert (pos > 0).sum() == 0              # fara cadere -> nicio intrare


def test_prefix_stable_no_lookahead():
    close = _crash_then_recover()
    full = dipbuy.dipbuy_positions(_bars(close), dip=0.2, lookback=20, exit_ma=10)
    pre = dipbuy.dipbuy_positions(_bars(close[:90]), dip=0.2, lookback=20, exit_ma=10)
    np.testing.assert_array_equal(full[:85], pre[:85])
