"""CLI TIER 2b: validare cross-sectionala a factorilor pe un univers larg.

    python validate_xs_cli.py                       # implicit data/sp500.csv
    python validate_xs_cli.py --universe data/sp500.csv --split 0.6

Pentru fiecare factor (momentum, reversal, low_vol, resmom, amihud) afiseaza
Sharpe full-sample, Sharpe OUT-OF-SAMPLE si p-value (sign-flip) pe streamul de
randamente NETE long-short. NU este consiliere de investitii.
"""

import argparse

from markov.validation.tier2b import load_universe, render_xs, run_xs_validation


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validare factori cross-sectionali.")
    ap.add_argument("--universe", default="data/sp500.csv",
                    help="CSV panel long (date, close, volume, Name)")
    ap.add_argument("--split", type=float, default=0.6,
                    help="fractia in-sample (restul = OOS)")
    ap.add_argument("--n-perm", type=int, default=2000,
                    help="permutari pentru p-value (sign-flip)")
    args = ap.parse_args(argv)

    rows = run_xs_validation(args.universe, split_frac=args.split, n_perm=args.n_perm)
    _P, _V, _d = load_universe(args.universe)
    print(render_xs(rows, n_assets=_P.shape[1]))


if __name__ == "__main__":
    main()
