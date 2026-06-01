"""Combined-signal portfolio backtest (shared by the validation harnesses).

Each rebalance day, build the equal-weight blend of the cross-sectional
signals (reversal + residual-momentum, plus illiquidity when volume is
given), form a dollar-neutral book proportional to the blended signal, and
hold it `holding` days net of turnover cost. This is the portfolio-level
view of what the per-asset SignalEngine emits -- the honest unit of
validation (a single asset is too noisy).

Panel convention: prices/volume shape (T, N); decisions at day t use data
up to t only (no look-ahead).
"""

import numpy as np

from markov.amihud import illiquidity_scores
from markov.resmom import residual_momentum_scores


def _centered_ranks(scores):
    order = scores.argsort()
    r = np.empty(len(scores))
    r[order] = np.arange(len(scores))
    return r / (len(scores) - 1) - 0.5  # [-0.5, 0.5]


def signal_portfolio_returns(prices, volume=None, rev_lb=10, lookback=126,
                             skip=21, holding=5, cost=2e-4):
    """Daily returns of the combined cross-sectional signal portfolio."""
    prices = np.asarray(prices, dtype=float)
    if volume is not None:
        volume = np.asarray(volume, dtype=float)
    T, N = prices.shape
    start = max(rev_lb + 1, lookback + skip + 1)
    if start >= T:
        raise ValueError(f"need more than {start} rows, have {T}")

    daily = []
    prev_w = np.zeros(N)
    t = start
    while t < T - 1:
        rev = -_centered_ranks(prices[t] / prices[t - rev_lb] - 1.0)   # long losers
        rm = _centered_ranks(residual_momentum_scores(prices, t, lookback, skip))
        parts = [rev, rm]
        if volume is not None:
            il = illiquidity_scores(prices, volume, t, 20)
            fin = np.isfinite(il)
            il = np.where(fin, il, np.nanmedian(il[fin]) if fin.any() else 0.0)
            parts.append(_centered_ranks(il))                          # long illiquid
        sig = np.mean(parts, axis=0)
        sig = sig - sig.mean()                                         # dollar-neutral
        gross = np.abs(sig).sum()
        w = sig / gross if gross > 0 else sig
        turnover = np.abs(w - prev_w).sum()
        charged = False
        for _ in range(holding):
            if t >= T - 1:
                break
            r = float(np.dot(w, prices[t + 1] / prices[t] - 1.0))
            if not charged:
                r -= cost * turnover
                charged = True
            daily.append(r)
            t += 1
        prev_w = w
    return np.array(daily)
