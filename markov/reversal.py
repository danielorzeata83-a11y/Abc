"""Cross-sectional short-term reversal.

The mirror image of momentum at short horizons: rank assets by their
trailing `lookback`-day return, go LONG the biggest losers and SHORT the
biggest winners, rebalance every `holding` days. Documented as one of the
most persistent equity anomalies (Lehmann 1990; Lo & MacKinlay 1990), and
it tends to pay precisely in trending markets where long-short momentum
suffers.

High turnover is the catch, so this charges an explicit per-unit-turnover
cost. Panel convention: prices shape (T, N); decisions at day t use
prices[:t+1] only.
"""

import numpy as np


def _reversal_weights(scores, top_frac):
    """Long the lowest scores (losers), short the highest (winners)."""
    n = len(scores)
    k = max(1, int(round(n * top_frac)))
    order = np.argsort(scores)
    losers, winners = order[:k], order[-k:]
    w = np.zeros(n)
    w[losers] = 1.0 / k       # long the losers (expect bounce)
    w[winners] = -1.0 / k     # short the winners (expect pullback)
    return w


def xs_reversal_returns(prices, lookback=5, holding=1, top_frac=0.2,
                        cost=0.001):
    """Net daily returns of a rebalanced cross-sectional reversal portfolio.

    At each rebalance day t, score_i = trailing `lookback`-day return,
    form long-loser / short-winner equal-weight legs, hold `holding`
    days. Charges `cost` per unit of turnover when weights change.
    """
    prices = np.asarray(prices, dtype=float)
    T, N = prices.shape
    if lookback >= T:
        raise ValueError(f"lookback={lookback} too large for T={T}")

    daily = []
    prev_w = np.zeros(N)
    t = lookback
    while t < T - 1:
        scores = prices[t] / prices[t - lookback] - 1.0
        w = _reversal_weights(scores, top_frac)
        turnover = np.abs(w - prev_w).sum()
        charged = False
        for _ in range(holding):
            if t >= T - 1:
                break
            day_ret = prices[t + 1] / prices[t] - 1.0
            r = float(np.dot(w, day_ret))
            if not charged:
                r -= cost * turnover  # pay rebalancing cost on first day
                charged = True
            daily.append(r)
            t += 1
        prev_w = w
    return np.array(daily)
