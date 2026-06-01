"""CLI: generate a buy/sell signal for a ticker.

Hybrid SignalEngine over a CSV panel. With --universe the ticker is
signalled cross-sectionally against the whole panel; with --single only
the ticker's own price series is used (time-series mode, low confidence).

Examples:
    python signal_cli.py --ticker NVDA --universe data/sp500.csv
    python signal_cli.py --ticker NVDA --universe data/sp500.csv --single

The bundled data/sp500.csv (2013-2018) already contains NVDA. Nothing here
is investment advice.
"""

import argparse

import numpy as np
import pandas as pd

from markov.engine import SignalEngine


def load_panel(path):
    raw = pd.read_csv(path)
    close = raw.pivot(index="date", columns="Name", values="close").sort_index()
    close = close.dropna(axis=1)
    volume = (raw.pivot(index="date", columns="Name", values="volume")
              .sort_index()[close.columns])
    return close, volume


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--universe", required=True, help="CSV panel path")
    ap.add_argument("--single", action="store_true",
                    help="time-series mode on the ticker only")
    ap.add_argument("--threshold", type=float, default=0.15)
    args = ap.parse_args()

    close, volume = load_panel(args.universe)
    if args.ticker not in close.columns:
        raise SystemExit(f"{args.ticker} not in {args.universe} "
                         f"({close.shape[1]} tickers)")
    dates = pd.to_datetime(close.index).to_numpy()
    engine = SignalEngine(threshold=args.threshold)

    if args.single:
        series = close[args.ticker].to_numpy()
        sig = engine.generate(series, dates=dates, ticker=args.ticker)
    else:
        idx = list(close.columns).index(args.ticker)
        sig = engine.generate(close.to_numpy(), dates=dates, target_idx=idx,
                              volume=volume.to_numpy().astype(float),
                              ticker=args.ticker)
    print(sig.render())


if __name__ == "__main__":
    main()
