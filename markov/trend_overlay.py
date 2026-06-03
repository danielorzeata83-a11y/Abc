"""Hindsight vs real-time trend overlay primitives.

Pure, causal functions for the educational NVDA chart: simple moving averages,
golden/death crossovers (using only past data), the hindsight major bottom, and
the lesson metrics (lag cost of waiting for confirmation, whipsaw count, and the
drawdown the signal sat through). Nothing here is investment advice.
"""

from collections import namedtuple

import numpy as np

Crossover = namedtuple("Crossover", ["idx", "kind"])  # kind: "golden" | "death"


def sma(prices, window):
    """Simple trailing moving average; first `window-1` entries are NaN.

    Causal: out[i] uses only prices[i-window+1 .. i] (no look-ahead).
    """
    if window <= 0:
        raise ValueError("window must be positive")
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    out = np.full(n, np.nan)
    if n < window:
        return out
    c = np.cumsum(np.insert(prices, 0, 0.0))   # c[k] = sum(prices[:k])
    out[window - 1:] = (c[window:] - c[:-window]) / window
    return out


def sma_crossovers(prices, fast=50, slow=200):
    """Golden (fast SMA crosses above slow) / death (below) crossovers.

    Causal: both SMAs use only past data. Returns Crossover(idx, kind) at the
    day the sign of (fast - slow) flips. Days where either SMA is NaN are skipped.
    """
    f = sma(prices, fast)
    s = sma(prices, slow)
    diff = f - s
    out = []
    prev = None
    for i in range(len(diff)):
        if not np.isfinite(diff[i]):
            continue
        above = diff[i] > 0
        if prev is not None and above != prev:
            out.append(Crossover(i, "golden" if above else "death"))
        prev = above
    return out


def hindsight_bottom(prices):
    """Index of the major bottom (global minimum).

    The clean, parameter-free 'from here up it was bull' marker -- only
    knowable in hindsight. That is the whole point of the overlay.
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) == 0:
        raise ValueError("empty price series")
    return int(np.nanargmin(prices))
