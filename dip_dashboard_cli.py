"""Genereaza dashboard-ul HTML 'dip-watch' (self-contained, offline) pentru un
watchlist. Faza 1: snapshot de stare, fara grafice. NU consiliere de investitii.

    python dip_dashboard_cli.py --watchlist NVDA,AAPL,MSFT --universe data/sp500.csv --out dip.html
    python dip_dashboard_cli.py --price-csv data/btc.csv:time:PriceUSD --name BTC --out btc.html
"""

import argparse
import sys

import numpy as np
import pandas as pd

from markov.dip_dashboard import build_html, dashboard_rows
from markov.intraday.cache import read_bars
from markov.intraday.price_series import load_price_series


def _closes(symbol, data_dir, universe):
    if universe:
        raw = pd.read_csv(universe)
        g = raw[raw["Name"].astype(str) == str(symbol)].sort_values("date")
        return g["close"].to_numpy(dtype=float) if not g.empty else None
    bars = read_bars(data_dir, symbol)
    return np.asarray(bars.close, dtype=float) if bars is not None else None


def _items(args):
    if args.price_csv:
        path, dc, pc = args.price_csv.split(":")
        return [(args.name, np.asarray(load_price_series(path, dc, pc).close, dtype=float))]
    syms = [s for s in (args.watchlist or "").split(",") if s.strip()]
    if not syms:
        raise SystemExit("Da --watchlist (+ --universe/--data-dir) sau --price-csv.")
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    return [(s.upper(), _closes(s.upper(), args.data_dir, args.universe)) for s in syms]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dashboard HTML dip-watch (faza 1).")
    ap.add_argument("--watchlist")
    ap.add_argument("--data-dir")
    ap.add_argument("--universe")
    ap.add_argument("--price-csv", help="cale:datecol:pricecol")
    ap.add_argument("--name", default="ASSET")
    ap.add_argument("--asof", default="")
    ap.add_argument("--lookback", type=int, default=60)
    ap.add_argument("--dip", type=float, default=0.4)
    ap.add_argument("--exit-ma", type=int, default=20)
    ap.add_argument("--out", default="dip_dashboard.html")
    args = ap.parse_args(argv)

    rows = dashboard_rows(_items(args), lookback=args.lookback, dip=args.dip,
                          exit_ma=args.exit_ma)
    html = build_html(rows, asof=args.asof, dip=args.dip)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    n = sum(1 for r in rows if r["state"] == "deep")
    print(f"Scris {args.out} ({len(rows)} active, {n} in dip adanc).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
