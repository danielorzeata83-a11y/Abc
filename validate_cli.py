"""CLI: ruleaza motorul de validare pe cei 13 indicatori TIER 1.

    python validate_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday

Citeste cache-ul 15m existent (vezi intraday_server.py pentru backfill).
NU este consiliere de investitii.
"""

import argparse

from markov.validation import TIERS
from markov.validation.report import run_validation
from markov.intraday.service import Config


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validare indicatori (A->E).")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir")
    ap.add_argument("--horizons", default="1,5,21",
                    help="orizonturi forward in bare (daily)")
    ap.add_argument("--target", default="return", choices=["return", "vol"],
                    help="tinta predictiei: randament (directie) sau vol (volatilitate)")
    ap.add_argument("--indicators", default="tier1", choices=list(TIERS))
    ap.add_argument("--out", help="scrie si CSV la calea data")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else list(cfg.watchlist))
    data_dir = args.data_dir or cfg.data_dir
    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())

    rep = run_validation(symbols, data_dir, TIERS[args.indicators], horizons=horizons,
                         target=args.target)
    print(rep.render_text())
    if args.out:
        rep.to_csv(args.out)
        print(f"\nCSV scris in {args.out}")


if __name__ == "__main__":
    main()
