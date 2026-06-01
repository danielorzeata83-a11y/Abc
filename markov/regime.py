"""Market-trend regime gate for crypto (no look-ahead).

Crypto cross-sectional momentum pays in trending/risk-on regimes and bleeds
in choppy/crash regimes (see results/crypto_validation.md). A simple,
a-priori regime gate: hold the book only when the equal-weight crypto index
is above its own moving average; otherwise stand flat.

The gate at day t uses only prices up to t. This is the single
highest-overfitting-risk component in the project, so windows are chosen
a priori and judged on sub-period consistency, not on a tuned OOS number.
"""

import numpy as np


def market_index(prices):
    """Equal-weight crypto index level from per-coin prices.

    Built from the cross-sectional mean daily return (scale-free, so BTC's
    large nominal price doesn't dominate), cumulated to a level series.
    """
    prices = np.asarray(prices, dtype=float)
    rets = prices[1:] / prices[:-1] - 1.0
    ew = np.nanmean(rets, axis=1)
    level = np.empty(prices.shape[0])
    level[0] = 1.0
    level[1:] = np.cumprod(1.0 + ew)
    return level


def market_trend_gate(prices, window=100):
    """1.0 when the EW index is above its `window`-day MA, else 0.0.

    The first `window` days are 0.0 (insufficient history -> risk-off).
    Uses only past data at each day (no look-ahead).
    """
    level = market_index(prices)
    T = len(level)
    gate = np.zeros(T)
    for t in range(window, T):
        ma = level[t - window:t].mean()
        gate[t] = 1.0 if level[t] > ma else 0.0
    return gate
