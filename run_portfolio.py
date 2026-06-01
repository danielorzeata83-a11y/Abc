"""Reproducible end-to-end run of the 6-edge market-neutral + timing portfolio.

Loads the S&P 500 panel, computes the six validated edges, prints their
individual out-of-sample stats, the correlation matrix, and the
equal-risk combined portfolio (weights estimated on the train split only).

The six edges (see results/REPORT.md for the full research narrative):
  Market-neutral alphas : Rev10, Rev3, Amihud, ResidualMomentum
  Market-timing edges   : TurnOfMonth, VolManaged

Usage:
    python run_portfolio.py [--data data/sp500.csv] [--cost-bps 2]

Nothing here is investment advice.
"""

import argparse

import numpy as np
import pandas as pd

from markov.reversal import xs_reversal_returns
from markov.seasonality import turn_of_month_returns
from markov.voltarget import vol_target_returns
from markov.amihud import xs_amihud_returns
from markov.resmom import xs_residual_momentum_returns
from markov.portfolio import combine_alphas, orthogonalize

PPY = 252  # trading days per year


def _stats(daily):
    eq = np.cumprod(1 + daily)
    vol = daily.std() * np.sqrt(PPY)
    sharpe = (daily.mean() * PPY) / vol if vol > 0 else 0.0
    peak = np.maximum.accumulate(eq)
    maxdd = ((eq - peak) / peak).min()
    return eq[-1] - 1, sharpe, maxdd


def load_panel(path):
    raw = pd.read_csv(path)
    close = raw.pivot(index="date", columns="Name", values="close").sort_index()
    close = close.dropna(axis=1)
    volume = (raw.pivot(index="date", columns="Name", values="volume")
              .sort_index()[close.columns].to_numpy().astype(float))
    dates = pd.to_datetime(close.index)
    return close.to_numpy(), volume, dates


def build_edges(prices, volume, dates, cost):
    ew = (prices[1:] / prices[:-1] - 1).mean(axis=1)
    vm, _ = vol_target_returns(ew, target_vol=0.15, window=20, max_leverage=3.0)
    edges = {
        "Rev10": xs_reversal_returns(prices, 10, 5, 0.1, cost=cost),
        "Rev3": xs_reversal_returns(prices, 3, 3, 0.1, cost=cost),
        "Amihud": xs_amihud_returns(prices, volume, 20, 21, 0.1, cost=cost),
        "ResMom": xs_residual_momentum_returns(prices, 126, 21, 21, 0.1, cost=cost),
        "TurnOfMonth": turn_of_month_returns(ew, dates[1:], 3, 3),
        "VolManaged": vm,
    }
    # Tail-align every stream to the shortest (residual momentum warms up last).
    m = min(len(s) for s in edges.values())
    return {k: v[-m:] for k, v in edges.items()}, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/sp500.csv")
    ap.add_argument("--cost-bps", type=float, default=2.0)
    ap.add_argument("--train-frac", type=float, default=0.6)
    args = ap.parse_args()

    prices, volume, dates = load_panel(args.data)
    edges, m = build_edges(prices, volume, dates, cost=args.cost_bps / 1e4)
    names = list(edges)
    streams = [edges[n] for n in names]
    split = int(m * args.train_frac)
    mn_names = ["Rev10", "Rev3", "Amihud", "ResMom"]  # market-neutral sleeve

    print(f"Panel: {prices.shape[0]} days x {prices.shape[1]} tickers")
    print(f"Aligned edge window: {m} days | cost {args.cost_bps}bps | "
          f"train {int(args.train_frac*100)}%\n")

    print("Individual edges (OOS):")
    print(f"  {'edge':<14}{'Sharpe':>8}{'ret':>9}{'MaxDD':>8}")
    for n in names:
        r, s, d = _stats(edges[n][split:])
        print(f"  {n:<14}{s:>8.2f}{r*100:>8.0f}%{d*100:>7.0f}%")

    print("\nCorrelation matrix (full sample):")
    C = np.corrcoef(np.vstack(streams))
    print("            " + "".join(f"{n[:6]:>8}" for n in names))
    for i, n in enumerate(names):
        print(f"  {n:<10}" + "".join(f"{C[i, j]:>8.2f}" for j in range(len(names))))

    def combo_oos(sel):
        strs = [edges[n] for n in sel]
        v = np.array([s[:split].std() for s in strs])
        w = (1 / v) / (1 / v).sum()
        return combine_alphas([s[split:] for s in strs], 0.10, weights=w)

    print("\nCombined portfolios (OOS, equal-risk, train-fit weights):")
    for label, sel in [("ALL-6", names),
                        ("MN-only (4 alphas)", mn_names)]:
        r, s, d = _stats(combo_oos(sel))
        print(f"  {label:<22} Sharpe {s:+.2f}  ret {r*100:+.0f}%  DD {d*100:.0f}%")

    print("\nIndependence check (orthogonal residual OOS Sharpe vs other 5):")
    for n in names:
        others = [edges[o] for o in names if o != n]
        resid = orthogonalize(edges[n], others)
        _, s, _ = _stats(resid[split:])
        print(f"  {n:<14}{s:+.2f}")

    print("\nNote: research artifact, not investment advice. See results/REPORT.md")


if __name__ == "__main__":
    main()
