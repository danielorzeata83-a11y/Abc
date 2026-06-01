"""Market-neutral low-volatility factor.

The low-volatility anomaly: stocks with lower trailing volatility tend to
deliver better risk-adjusted returns than high-vol stocks. Implemented as
a dollar-neutral long-short -- long the lowest-vol names, short the
highest -- it is a second alpha source largely independent of short-term
reversal.

Panel convention: prices shape (T, N); decisions at day t use prices[:t+1].
"""

import numpy as np


def trailing_vol_scores(prices, t=None, window=60):
    """Trailing daily-return volatility of each asset as of day t."""
    prices = np.asarray(prices, dtype=float)
    if t is None:
        t = prices.shape[0] - 1
    rets = prices[t - window + 1:t + 1] / prices[t - window:t] - 1.0
    return rets.std(axis=0)


def xs_lowvol_returns(prices, vol_window=60, holding=21, top_frac=0.2,
                      cost=0.001):
    """Net daily returns of a dollar-neutral low-vol long-short portfolio.

    Long the `top_frac` lowest-volatility names, short the highest, rebal
    every `holding` days, charging `cost` per unit turnover.
    """
    prices = np.asarray(prices, dtype=float)
    T, N = prices.shape
    if vol_window >= T:
        raise ValueError(f"vol_window={vol_window} too large for T={T}")

    k = max(1, int(round(N * top_frac)))
    daily = []
    prev_w = np.zeros(N)
    t = vol_window
    while t < T - 1:
        vol = trailing_vol_scores(prices, t, vol_window)
        order = vol.argsort()
        low, high = order[:k], order[-k:]   # low vol = long
        w = np.zeros(N)
        w[low] = 1.0 / k
        w[high] = -1.0 / k
        turnover = np.abs(w - prev_w).sum()
        charged = False
        for _ in range(holding):
            if t >= T - 1:
                break
            day_ret = prices[t + 1] / prices[t] - 1.0
            r = float(np.dot(w, day_ret))
            if not charged:
                r -= cost * turnover
                charged = True
            daily.append(r)
            t += 1
        prev_w = w
    return np.array(daily)
