"""Sistem BUY-THE-DIP (long-only), codificat MECANIC si CAUZAL -- "cumpara cat
e jos" pus la incercare onesta:

1. Drawdown: cat de jos e pretul fata de maximul ultimelor `lookback` zile.
2. Intrare: cand drawdown <= -`dip` (pretul a cazut destul de mult sub varf).
3. Iesire: cand pretul revine deasupra unei MA scurte (`exit_ma`) -- s-a redresat.

Pragul `dip` se alege prin walk-forward (markov.wfselect), NU din burta.
NU consiliere de investitii -- harness de testare onesta.
"""

import numpy as np
import pandas as pd

from markov.trendpull import ma


def rolling_high(close, lookback=60):
    """Maximul mobil al inchiderii pe `lookback` (NaN pe warmup, cauzal)."""
    return pd.Series(np.asarray(close, dtype=float)).rolling(
        lookback, min_periods=lookback).max().to_numpy()


def drawdown(close, lookback=60):
    """close/rolling_high - 1  (<= 0): cat de jos fata de varful recent."""
    close = np.asarray(close, dtype=float)
    return close / rolling_high(close, lookback) - 1.0


def dipbuy_positions(bars, dip=0.2, lookback=60, exit_ma=20):
    """Pozitie long-only {0, +1}: cumpara dipul, vinde la redresare. Cauzal."""
    close = np.asarray(bars.close, dtype=float)
    n = len(close)
    dd = drawdown(close, lookback)
    ma_s = ma(close, exit_ma)

    positions = np.zeros(n)
    pos, state = 0.0, "FLAT"
    for t in range(n):
        start = state
        if start == "LONG":
            if not np.isnan(ma_s[t]) and close[t] > ma_s[t]:
                pos, state = 0.0, "FLAT"
        if start == "FLAT":
            if not np.isnan(dd[t]) and dd[t] <= -dip:
                pos, state = 1.0, "LONG"
        positions[t] = pos
    return positions
