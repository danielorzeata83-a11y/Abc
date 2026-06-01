"""Volatility targeting for equal-risk comparison.

To compare two strategies fairly we put them on the same risk budget:
scale each daily return stream so its trailing realised volatility tracks
a common annual target. Leverage on day t is computed from the trailing
window of PAST returns only, so there is no look-ahead.
"""

import numpy as np

_ANN = np.sqrt(365)  # daily -> annual for crypto (24/7)


def realised_vol(returns):
    """Annualised volatility of a daily return series."""
    returns = np.asarray(returns, dtype=float)
    return float(returns.std() * _ANN)


def vol_target_returns(returns, target_vol=0.20, window=60, max_leverage=5.0):
    """Scale `returns` toward a constant annual volatility target.

    Returns (scaled_returns, leverage). leverage[t] = target /
    trailing_vol(returns[t-window:t]), capped at max_leverage. The first
    `window` days have no estimate and are set to zero leverage.
    """
    returns = np.asarray(returns, dtype=float)
    n = len(returns)
    if window >= n:
        raise ValueError(f"window={window} too large for {n} returns")

    lev = np.zeros(n, dtype=float)
    for t in range(window, n):
        past_vol = returns[t - window:t].std() * _ANN
        if past_vol > 0:
            lev[t] = min(target_vol / past_vol, max_leverage)
    scaled = lev * returns
    return scaled, lev
