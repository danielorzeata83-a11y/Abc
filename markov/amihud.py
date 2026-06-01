"""Amihud illiquidity factor (market-neutral).

Amihud (2002) illiquidity for an asset is the average ratio of absolute
return to dollar volume over a trailing window -- how much the price moves
per dollar traded. Illiquid names carry a return premium, so a
dollar-neutral long-illiquid / short-liquid portfolio is an alpha source
independent of reversal, calendar and vol-managed edges.

Panel convention: prices and volume have shape (T, N); decisions at day t
use data up to t only.
"""

import numpy as np


def illiquidity_scores(prices, volume, t=None, window=20):
    """Amihud illiquidity per asset as of day t (higher = less liquid)."""
    prices = np.asarray(prices, dtype=float)
    volume = np.asarray(volume, dtype=float)
    if t is None:
        t = prices.shape[0] - 1
    seg = slice(t - window, t)
    rets = prices[t - window + 1:t + 1] / prices[t - window:t] - 1.0
    dollar = prices[seg] * volume[seg]
    illiq = np.abs(rets) / np.where(dollar > 0, dollar, np.nan)
    return np.nanmean(illiq, axis=0)


def xs_amihud_returns(prices, volume, window=20, holding=21, top_frac=0.1,
                      cost=0.001):
    """Net daily returns of a dollar-neutral long-illiquid/short-liquid book."""
    prices = np.asarray(prices, dtype=float)
    volume = np.asarray(volume, dtype=float)
    T, N = prices.shape
    if window >= T:
        raise ValueError(f"window={window} too large for T={T}")

    k = max(1, int(round(N * top_frac)))
    daily = []
    prev_w = np.zeros(N)
    t = window
    while t < T - 1:
        sc = illiquidity_scores(prices, volume, t, window)
        fin = np.isfinite(sc)
        sc = np.where(fin, sc, np.nanmedian(sc[fin]) if fin.any() else 0.0)
        order = sc.argsort()
        liquid, illiquid = order[:k], order[-k:]   # high score = illiquid = long
        w = np.zeros(N)
        w[illiquid] = 1.0 / k
        w[liquid] = -1.0 / k
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
