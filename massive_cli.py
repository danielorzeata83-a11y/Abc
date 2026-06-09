"""Converteste flat files massive.com (descarcate de tine) in formatul nostru
lung -> intra direct in dashboard/monitor/alerta/backtest. ZERO retea, ZERO secret.

    # descarca fisierele cu tool-ul lor (local), apoi:
    python massive_cli.py --in "downloads/2026-*.csv.gz" --symbols NVDA,AAPL --out data/massive.csv
    python dip_dashboard_cli.py --watchlist NVDA,AAPL --universe data/massive.csv --out dip.html

NU consiliere de investitii.
"""

import argparse
import sys

from markov.massive_loader import load_flat_files


def main(argv=None):
    ap = argparse.ArgumentParser(description="Flat files massive -> CSV lung.")
    ap.add_argument("--in", dest="inputs", nargs="+", required=True,
                    help="fisiere sau pattern-uri glob (CSV/CSV.gz)")
    ap.add_argument("--symbols", help="filtru, separate prin virgula")
    ap.add_argument("--name", help="nume ticker pt fisiere fara coloana de ticker")
    ap.add_argument("--out", default="data/massive.csv")
    args = ap.parse_args(argv)

    syms = [s for s in (args.symbols or "").split(",") if s.strip()] or None
    df = load_flat_files(args.inputs, symbols=syms, default_name=args.name)
    df.to_csv(args.out, index=False)
    rng = f"{df['date'].min()} -> {df['date'].max()}" if len(df) else "gol"
    print(f"Scris {args.out}: {len(df)} randuri, {df['Name'].nunique()} simboluri, {rng}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
