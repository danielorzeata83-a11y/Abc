"""Genereaza un trading view HTML self-contained cu OHLCV REAL.

    python tradingview_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday
    python tradingview_cli.py --universe data/sp500.csv --symbols AAPL,MSFT,JPM,XOM
    python tradingview_cli.py --out results/tradingview.html

Doua surse de date reale: cache-ul daily backfilled (--data-dir) sau un CSV long
OHLCV (--universe, ex. data/sp500.csv). Lumanari OHLC + volum + MA50 + markeri +
sub-panou z realized_var + strip lead-lag, cu zoom/pan. Offline, fara cereri
externe. NU consiliere de investitii.
"""

import argparse

import pandas as pd

from markov.intraday.service import Config
from markov.tradingview import (build_html, collect_panels, lead_lag_from_panels,
                                panels_from_long_csv)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Trading view HTML (OHLCV real).")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir", help="cache daily backfilled (read_bars)")
    ap.add_argument("--universe", help="CSV long OHLCV (date,open,high,low,close,volume,Name)")
    ap.add_argument("--out", default="results/tradingview.html")
    ap.add_argument("--max-bars", type=int, default=750,
                    help="cate bare recente sa afiseze per simbol")
    ap.add_argument("--asof", help="data raportului (YYYY-MM-DD); implicit azi")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else None)
    asof = args.asof or pd.Timestamp.now().strftime("%Y-%m-%d")

    if args.universe:
        panels = panels_from_long_csv(args.universe, symbols=symbols,
                                      max_bars=args.max_bars)
        src = args.universe
    else:
        data_dir = args.data_dir or cfg.data_dir
        panels = collect_panels(symbols or list(cfg.watchlist), data_dir,
                                max_bars=args.max_bars)
        src = data_dir
    if not panels:
        raise SystemExit(f"Niciun simbol gasit in {src}. Verifica --symbols / backfill.")

    leadlag = lead_lag_from_panels(panels)
    html = build_html(panels, asof, leadlag=leadlag)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Scris {args.out} ({len(panels)} simboluri, {len(html)//1024} KB) din {src}.")


if __name__ == "__main__":
    main()
