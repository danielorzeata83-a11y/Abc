"""Fibonacci swing detection and retracement levels.

Mechanical (objective) implementation so the "Fibonacci probability" claims
can be TESTED rather than asserted. find_swings is a threshold zig-zag that
yields alternating swing highs/lows; fib_levels gives the retracement prices
for a leg. No look-ahead in fib_levels (it's pure geometry on a known leg);
the validation harness is responsible for using only past swings.
"""

import numpy as np

STD_LEVELS = (0.382, 0.5, 0.618, 0.786, 0.886)


def fib_levels(swing_start, swing_end, levels=STD_LEVELS):
    """Retracement prices for a leg from swing_start to swing_end.

    0% sits at swing_end, 100% at swing_start; level L gives the price L of
    the way retraced back toward the start. Works for up- and down-legs.
    """
    rng = swing_end - swing_start
    return {L: swing_end - L * rng for L in levels}


def find_swings(prices, threshold=0.05):
    """Threshold zig-zag: alternating (index, price, 'H'|'L') swing points.

    A reversal is confirmed once price moves `threshold` (fractional) away
    from the running extreme, which is then recorded as a swing point.
    """
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    if n < 2:
        return []

    swings = []
    pivot_i, pivot_v, trend = 0, prices[0], 0
    for i in range(1, n):
        p = prices[i]
        if trend == 0:
            if p >= pivot_v * (1 + threshold):
                trend, pivot_v, pivot_i = 1, p, i
            elif p <= pivot_v * (1 - threshold):
                trend, pivot_v, pivot_i = -1, p, i
            continue
        if trend == 1:
            if p > pivot_v:
                pivot_v, pivot_i = p, i
            elif p <= pivot_v * (1 - threshold):
                swings.append((pivot_i, pivot_v, "H"))
                trend, pivot_v, pivot_i = -1, p, i
        else:  # trend == -1
            if p < pivot_v:
                pivot_v, pivot_i = p, i
            elif p >= pivot_v * (1 + threshold):
                swings.append((pivot_i, pivot_v, "L"))
                trend, pivot_v, pivot_i = 1, p, i

    swings.append((pivot_i, pivot_v, "H" if trend >= 0 else "L"))
    return swings
