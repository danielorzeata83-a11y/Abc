"""Genereaza un trading view HTML self-contained din cache-ul daily.

    python tradingview_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday
    python tradingview_cli.py --out results/tradingview.html

Lumanari OHLC + volum + sub-panou cu semnalul de volatilitate (z realized_var),
crosshair si comutator de simboluri. Offline, fara cereri externe. NU consiliere
de investitii.
"""

import argparse

import pandas as pd

from markov.intraday.service import Config
from markov.tradingview import build_html, collect_panels


def main(argv=None):
    ap = argparse.ArgumentParser(description="Trading view HTML din cache.")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir")
    ap.add_argument("--out", default="results/tradingview.html")
    ap.add_argument("--max-bars", type=int, default=750,
                    help="cate bare recente sa afiseze per simbol")
    ap.add_argument("--asof", help="data raportului (YYYY-MM-DD); implicit azi")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else list(cfg.watchlist))
    data_dir = args.data_dir or cfg.data_dir
    asof = args.asof or pd.Timestamp.now().strftime("%Y-%m-%d")

    panels = collect_panels(symbols, data_dir, max_bars=args.max_bars)
    if not panels:
        raise SystemExit(f"Niciun simbol in cache ({data_dir}). Ruleaza intai backfill_cli.")
    html = build_html(panels, asof)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Scris {args.out} ({len(panels)} simboluri, {len(html)//1024} KB).")


if __name__ == "__main__":
    main()
