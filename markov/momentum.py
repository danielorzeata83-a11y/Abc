"""Cross-sectional (portfolio) momentum.

Rank a universe of assets by their trailing return, go long the winners
and (optionally) short the losers, rebalance every `holding` days. Unlike
single-asset timing, the idiosyncratic noise of any one name averages out
across the panel -- which is why momentum is one of the few anomalies
that survives out-of-sample in the academic literature
(Jegadeesh & Titman 1993; Moskowitz, Ooi & Pedersen 2012).

Panel convention: prices has shape (T, N) -- T days, N assets. Every
decision on rebalance day t uses prices[:t+1] only (no look-ahead).
"""

import numpy as np


def momentum_scores(prices, lookback=126, skip=21, as_of=None):
    """Trailing return of each asset, skipping the most recent `skip` days.

    score_i = price[as_of - skip] / price[as_of - skip - lookback] - 1.
    Skipping the last month avoids the well-known short-term reversal.
    `as_of` defaults to the last row.
    """
    prices = np.asarray(prices, dtype=float)
    t = (prices.shape[0] - 1) if as_of is None else as_of
    end = t - skip
    start = end - lookback
    if start < 0:
        raise ValueError("not enough history for lookback+skip")
    return prices[end] / prices[start] - 1.0


def _weights_from_scores(scores, top_frac, long_short):
    """Equal-weight long top fraction, short bottom fraction (if enabled)."""
    n = len(scores)
    k = max(1, int(round(n * top_frac)))
    order = np.argsort(scores)
    losers, winners = order[:k], order[-k:]
    w = np.zeros(n)
    w[winners] = 1.0 / k
    if long_short:
        w[losers] = -1.0 / k
    return w


def xs_momentum_returns(prices, lookback=126, skip=21, holding=21,
                        top_frac=0.2, long_short=True):
    """Daily returns of a rebalanced cross-sectional momentum portfolio.

    At each rebalance day, rank assets by `momentum_scores`, form
    equal-weight long (and short) legs, then hold for `holding` days
    earning each day's panel returns under fixed weights.
    """
    prices = np.asarray(prices, dtype=float)
    T, N = prices.shape
    first = lookback + skip
    if first >= T:
        raise ValueError(f"lookback+skip={first} too large for T={T}")

    daily = []
    t = first
    while t < T - 1:
        scores = momentum_scores(prices, lookback, skip, as_of=t)
        w = _weights_from_scores(scores, top_frac, long_short)
        # Hold weights fixed for the next `holding` days (or until the end).
        for h in range(holding):
            if t >= T - 1:
                break
            day_ret = prices[t + 1] / prices[t] - 1.0
            daily.append(float(np.dot(w, day_ret)))
            t += 1
    return np.array(daily)
