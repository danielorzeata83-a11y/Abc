"""Honesty harness: validate the engine's cross-sectional signal as a portfolio.

A single-ticker backtest is too noisy to trust (the central lesson of this
project). The honest validation is at PORTFOLIO level: each rebalance day,
form the combined cross-sectional signal (reversal + residual-momentum +
amihud rank, equal weight) for EVERY stock, build a dollar-neutral book
proportional to those signals, and backtest it out-of-sample net of costs.

This shows whether the per-asset signal the CLI emits aggregates into a
real edge. Nothing here is investment advice.
"""

import numpy as np
import pandas as pd

from markov.amihud import illiquidity_scores
from markov.resmom import residual_momentum_scores

PPY = 252


def _stats(d, split):
    def sh(x):
        v = x.std() * np.sqrt(PPY)
        return (x.mean() * PPY) / v if v > 0 else 0.0
    return sh(d), sh(d[split:])


def _ranks(scores):
    order = scores.argsort()
    r = np.empty(len(scores))
    r[order] = np.arange(len(scores))
    return r / (len(scores) - 1) - 0.5  # [-0.5, 0.5]


def main():
    raw = pd.read_csv("data/sp500.csv")
    close = raw.pivot(index="date", columns="Name", values="close").sort_index().dropna(axis=1)
    cols = close.columns
    volume = raw.pivot(index="date", columns="Name", values="volume").sort_index()[cols].to_numpy().astype(float)
    P = close.to_numpy()
    T, N = P.shape
    cost, holding, lookback, skip, vw, rev_lb = 2e-4, 5, 126, 21, 20, 10

    daily = []
    prev_w = np.zeros(N)
    t = lookback + skip + 1
    start = t
    while t < T - 1:
        rev = -_ranks(P[t] / P[t - rev_lb] - 1.0)            # long losers
        rm = _ranks(residual_momentum_scores(P, t, lookback, skip))  # long winners
        il = illiquidity_scores(P, volume, t, vw)
        fin = np.isfinite(il); il = np.where(fin, il, np.nanmedian(il[fin]))
        am = _ranks(il)                                       # long illiquid
        sig = (rev + rm + am) / 3.0
        sig = sig - sig.mean()                                # dollar-neutral
        w = sig / np.abs(sig).sum()                           # unit gross
        to = np.abs(w - prev_w).sum()
        charged = False
        for _ in range(holding):
            if t >= T - 1:
                break
            r = float(np.dot(w, P[t + 1] / P[t] - 1.0))
            if not charged:
                r -= cost * to
                charged = True
            daily.append(r)
            t += 1
        prev_w = w

    daily = np.array(daily)
    split = int(len(daily) * 0.6)
    full, oos = _stats(daily, split)
    eq = np.cumprod(1 + daily[split:])
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    print(f"Engine cross-sectional signal as a portfolio ({N} stocks, 2bps):")
    print(f"  full-sample Sharpe : {full:+.2f}")
    print(f"  out-of-sample Sharpe: {oos:+.2f}   OOS MaxDD {dd*100:.0f}%")
    print(f"  (per-ticker CLI signals are components of THIS portfolio edge)")
    print("  Research artifact - not investment advice.")


if __name__ == "__main__":
    main()
