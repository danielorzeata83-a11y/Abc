"""Classic technical indicators -- mechanical, hence testable.

RSI, MACD and Stochastic are exact functions of past prices. Unlike
discretionary chart concepts they can be coded and back-tested, so claims
about them can be checked rather than asserted. They are lagging
derivatives of price and carry no information beyond price itself.
No look-ahead: each value at index i uses prices[:i+1] only.
"""

import numpy as np


def _ema(values, span):
    values = np.asarray(values, dtype=float)
    alpha = 2.0 / (span + 1.0)
    out = np.empty_like(values)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(prices, period=14):
    """Wilder's RSI in [0, 100]; first `period` values are NaN."""
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_g = gain[:period].mean()
    avg_l = loss[:period].mean()
    for i in range(period, n):
        if i > period:
            avg_g = (avg_g * (period - 1) + gain[i - 1]) / period
            avg_l = (avg_l * (period - 1) + loss[i - 1]) / period
        rs = avg_g / avg_l if avg_l > 0 else np.inf
        out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def macd(prices, fast=12, slow=26, signal=9):
    """MACD line, signal line and histogram."""
    prices = np.asarray(prices, dtype=float)
    line = _ema(prices, fast) - _ema(prices, slow)
    sig = _ema(line, signal)
    return line, sig, line - sig


def stochastic_k(prices, period=14):
    """Stochastic %K in [0, 100] from close only; first values NaN."""
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        lo, hi = window.min(), window.max()
        out[i] = 100.0 * (prices[i] - lo) / (hi - lo) if hi > lo else 50.0
    return out


def ema_crossover(prices, fast=9, slow=20):
    """State signal: +1 when fast EMA is above slow EMA, -1 below.

    The "9/20 EMA crossover" of the intraday infographic, mechanised so it
    can be tested. Returns a per-bar state using only past prices.
    """
    prices = np.asarray(prices, dtype=float)
    diff = _ema(prices, fast) - _ema(prices, slow)
    return np.sign(diff)
