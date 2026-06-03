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
