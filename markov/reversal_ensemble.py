"""Enhanced ensemble cross-sectional reversal.

Refines single-horizon reversal two ways:

1. Ensemble across several lookbacks. Each lookback ranks the universe;
   we average the rank-based signal across horizons so no single noisy
   window dictates the trade. Smoother signals turn over less.

2. Inverse-volatility leg weighting. Within the long and short legs we
   weight by 1/vol (trailing) instead of equal weight, so a few very
   volatile names don't dominate portfolio risk (and rebalancing cost).

Panel convention: prices shape (T, N); decisions at day t use prices[:t+1].
"""

import numpy as np


def _rank_signal(prices, t, lookback):
    """Reversal signal in [-1, 1] per asset: high = recent loser (buy)."""
    scores = prices[t] / prices[t - lookback] - 1.0
    # Cross-sectional rank, centered: losers (low score) -> +, winners -> -.
    order = scores.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(scores))
    centered = ranks / (len(scores) - 1) - 0.5  # in [-0.5, 0.5]
    return -2.0 * centered  # losers positive


def _trailing_vol(prices, t, window=20):
    rets = prices[t - window + 1:t + 1] / prices[t - window:t] - 1.0
    v = rets.std(axis=0)
    v[v == 0] = np.nan
    return v


def xs_reversal_ensemble(prices, lookbacks=(3, 5, 10), holding=5,
                         top_frac=0.2, cost=0.001, inverse_vol=True,
                         vol_window=20):
    """Net daily returns of the ensemble reversal portfolio."""
    prices = np.asarray(prices, dtype=float)
    T, N = prices.shape
    start = max(max(lookbacks), vol_window if inverse_vol else 0)
    if start >= T:
        raise ValueError(f"start={start} too large for T={T}")

    k = max(1, int(round(N * top_frac)))
    daily = []
    prev_w = np.zeros(N)
    t = start
    while t < T - 1:
        # Average the reversal signal across lookbacks.
        sig = np.mean([_rank_signal(prices, t, lb) for lb in lookbacks],
                      axis=0)
        order = sig.argsort()
        losers, winners = order[-k:], order[:k]  # high sig = buy
        w = np.zeros(N)
        if inverse_vol:
            vol = _trailing_vol(prices, t, vol_window)
            iv = np.where(np.isfinite(vol), 1.0 / vol, 0.0)
            lw = iv[losers] / iv[losers].sum() if iv[losers].sum() > 0 else np.ones(k) / k
            sw = iv[winners] / iv[winners].sum() if iv[winners].sum() > 0 else np.ones(k) / k
            w[losers] = lw
            w[winners] = -sw
        else:
            w[losers] = 1.0 / k
            w[winners] = -1.0 / k

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
