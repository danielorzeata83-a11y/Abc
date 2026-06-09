"""CLI TIER 2: retea lead-lag cross-asset prin transfer entropy.

    python crossasset_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday

Citeste cache-ul daily, aliniaza randamentele pe datele comune, calculeaza TE(i->j)
intre toate perechile si afiseaza clasamentul lider->urmaritor. NU consiliere de investitii.
"""

import argparse

from markov.intraday.service import Config
from markov.validation.crossasset import (aligned_returns, lead_lag_matrix,
                                          render_lead_lag)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Retea lead-lag (transfer entropy).")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir")
    ap.add_argument("--bins", type=int, default=4, help="cosuri de discretizare")
    ap.add_argument("--lag", type=int, default=1, help="lag in bare daily")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else list(cfg.watchlist))
    data_dir = args.data_dir or cfg.data_dir

    rets = aligned_returns(symbols, data_dir)
    syms, M, net = lead_lag_matrix(rets, bins=args.bins, lag=args.lag)
    print(render_lead_lag(syms, M, net))
    print(f"\n({len(rets)} zile comune)")


if __name__ == "__main__":
    main()
