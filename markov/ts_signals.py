"""Single-asset (time-series) latest-position signals.

Each function returns today's target position in [-1, 1] for one price
series, using data up to the last bar only. These own-price signals are
weak out-of-sample (see results/REPORT.md) and are flagged low-confidence
by the engine; they exist so the hybrid engine still produces something
when only one chart is supplied.
"""

import numpy as np
import pandas as pd

from markov.seasonality import turn_of_month_mask

_ANN = np.sqrt(252)


def ts_momentum_position(prices, ma_window=50, scale=0.1):
    """Trend signal: sign/size of (price / moving-average - 1), clamped."""
    prices = np.asarray(prices, dtype=float)
    if len(prices) < ma_window:
        return 0.0
    ma = prices[-ma_window:].mean()
    gap = prices[-1] / ma - 1.0
    return float(np.clip(gap / scale, -1.0, 1.0))


def ts_reversal_position(prices, lookback=5):
    """Mean-reversion signal: negative of the recent return, vol-scaled.

    A recent drop -> positive (buy); a recent spike -> negative (sell).
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) < lookback + 1:
        return 0.0
    recent = prices[-1] / prices[-lookback - 1] - 1.0
    daily = prices[-lookback - 1:] [1:] / prices[-lookback - 1:][:-1] - 1.0
    vol = daily.std()
    if vol == 0:
        return 0.0
    z = recent / (vol * np.sqrt(lookback))
    return float(np.clip(-z, -1.0, 1.0))


def volmanaged_position(prices, target_vol=0.15, window=20, max_leverage=1.0):
    """Vol-managed long sizing: target / trailing annualised vol, in [0, cap].

    A directional-long sleeve sized by calm; smaller when volatile.
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) < window + 1:
        return 0.0
    rets = prices[-window - 1:][1:] / prices[-window - 1:][:-1] - 1.0
    vol = rets.std() * _ANN
    if vol <= 0:
        return 0.0
    return float(min(target_vol / vol, max_leverage))


def turn_of_month_position(dates, n_end=3, n_start=3):
    """Calendar signal: 1.0 if today is a turn-of-month day, else 0.0."""
    mask = turn_of_month_mask(np.asarray(dates), n_end=n_end, n_start=n_start)
    return 1.0 if bool(mask[-1]) else 0.0
