"""Residual (idiosyncratic) momentum.

Plain cross-sectional momentum loads on market/factor exposure and suffers
violent crashes. Residual momentum (Blitz, Huij & Martens 2011) first
regresses each stock's returns on the market over a lookback window, then
ranks stocks on their cumulated RESIDUAL return (skipping the most recent
month). Long residual winners / short residual losers -- market-neutral by
construction and historically more robust than plain momentum.

Panel convention: prices shape (T, N); decisions at day t use prices[:t+1].
"""

import numpy as np


def _market_returns(rets):
    """Equal-weight market return per day from a (W, N) return block."""
    return rets.mean(axis=1)


def residual_momentum_scores(prices, t=None, lookback=126, skip=21):
    """Cumulated market-residual return of each asset over the lookback
    window ending `skip` days before t (higher = idiosyncratic winner)."""
    prices = np.asarray(prices, dtype=float)
    if t is None:
        t = prices.shape[0] - 1
    end = t - skip
    start = end - lookback
    if start < 1:
        raise ValueError("not enough history for lookback+skip")
    rets = prices[start:end] / prices[start - 1:end - 1] - 1.0  # (lookback, N)
    mkt = _market_returns(rets)
    mkc = mkt - mkt.mean()
    var = mkt.var()
    if var == 0:
        return rets.sum(axis=0)
    beta = ((rets - rets.mean(axis=0)) * mkc[:, None]).mean(axis=0) / var
    resid = rets - np.outer(mkt, beta)
    return resid.sum(axis=0)


def xs_residual_momentum_returns(prices, lookback=126, skip=21, holding=21,
                                 top_frac=0.1, cost=0.001):
    """Net daily returns of a market-neutral residual-momentum portfolio."""
    prices = np.asarray(prices, dtype=float)
    T, N = prices.shape
    first = lookback + skip + 1
    if first >= T:
        raise ValueError(f"lookback+skip={lookback + skip} too large for T={T}")

    k = max(1, int(round(N * top_frac)))
    daily = []
    prev_w = np.zeros(N)
    t = first
    while t < T - 1:
        sc = residual_momentum_scores(prices, t, lookback, skip)
        order = sc.argsort()
        losers, winners = order[:k], order[-k:]
        w = np.zeros(N)
        w[winners] = 1.0 / k      # long residual winners
        w[losers] = -1.0 / k
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
