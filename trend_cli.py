"""Render an educational hindsight-vs-real-time trend chart for one ticker.

Overlays SMA fast/slow golden/death crosses and a walk-forward HMM regime on the
price, marks the hindsight bottom, and shows the 'cost of waiting' plus the
drawdown the signal sat through. Visualisation only -- NOT investment advice.

    python trend_cli.py --ticker NVDA --data data/sp500.csv
"""

import argparse
import os as _os

import numpy as np
import pandas as pd

from markov.trend_overlay import (sma, sma_crossovers, hindsight_bottom,
                                  lag_cost, count_whipsaws, signal_drawdown)
from markov.hmm_walkforward import hmm_walk_forward_states
from markov.trend_chart import render_trend_svg


def _DATA(name):
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", name)


def load_ticker(path, ticker):
    """Return (dates, close) for `ticker`, sorted by date."""
    raw = pd.read_csv(path)
    df = raw[raw["Name"] == ticker].sort_values("date")
    if df.empty:
        raise SystemExit(f"{ticker} not found in {path}")
    return df["date"].to_numpy(), df["close"].to_numpy(dtype=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="NVDA")
    ap.add_argument("--data", default=_DATA("sp500.csv"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--fast", type=int, default=50)
    ap.add_argument("--slow", type=int, default=200)
    args = ap.parse_args()

    dates, close = load_ticker(args.data, args.ticker)

    fast = sma(close, args.fast)
    slow = sma(close, args.slow)
    crossovers = sma_crossovers(close, args.fast, args.slow)
    bottom = hindsight_bottom(close)
    states, start = hmm_walk_forward_states(close)

    goldens = [c for c in crossovers if c.kind == "golden"]
    first_golden = goldens[0].idx if goldens else bottom
    entry = next((c.idx for c in goldens if c.idx >= bottom), first_golden)
    deaths = [c.idx for c in crossovers if c.kind == "death" and c.idx > entry]
    exit_idx = deaths[0] if deaths else len(close) - 1

    stats = {
        "lag_cost": lag_cost(close, bottom, first_golden),
        "whipsaws": count_whipsaws(crossovers, min_hold_days=30),
        "max_drawdown": signal_drawdown(close, entry, exit_idx),
        "fast": args.fast, "slow": args.slow,
    }

    svg = render_trend_svg(dates, close, fast, slow, crossovers,
                           states, start, bottom, stats)
    out = args.out or f"trend_{args.ticker}.html"
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{args.ticker} trend overlay</title></head><body>"
            f"<h1>{args.ticker}: hindsight vs real-time</h1>{svg}</body></html>")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
