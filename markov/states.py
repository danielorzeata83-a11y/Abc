"""State classification for the Markov hedge-fund method.

A "state" is a coarse regime label derived from recent price action:
BULL, BEAR, or SIDEWAYS. States are computed from a rolling window of
simple daily returns (see tests/test_states.py for the spec).
"""

from enum import IntEnum

import numpy as np


class State(IntEnum):
    BEAR = 0
    SIDEWAYS = 1
    BULL = 2
    UNKNOWN = -1


def daily_returns(prices):
    """Simple daily returns from a price series: r_t = P_t / P_{t-1} - 1."""
    prices = np.asarray(prices, dtype=float)
    return prices[1:] / prices[:-1] - 1.0


def classify_states(prices, window=20, threshold=0.05):
    """Label each day with its regime state.

    Returns an array of `State` values, one per daily return
    (i.e. len(prices) - 1 labels). The first `window` labels are UNKNOWN
    because they lack a full lookback window.
    """
    returns = daily_returns(prices)
    if len(returns) < window:
        raise ValueError(
            f"need at least {window} returns, got {len(returns)}"
        )

    states = np.full(len(returns), State.UNKNOWN, dtype=int)
    # Rolling sum of returns over the trailing `window` days.
    for i in range(window, len(returns) + 1):
        windowed = returns[i - window:i].sum()
        # Inclusive boundary, tolerant to floating-point summation error.
        if windowed >= threshold - 1e-9:
            label = State.BULL
        elif windowed <= -threshold + 1e-9:
            label = State.BEAR
        else:
            label = State.SIDEWAYS
        # Label is attached to the day at the end of the window.
        states[i - 1] = label

    return [State(s) for s in states]
