"""CLI TIER 2b: validare cross-sectionala a factorilor pe un univers larg.

    python validate_xs_cli.py                              # CSV implicit data/sp500.csv
    python validate_xs_cli.py --universe data/sp500.csv --split 0.6
    python validate_xs_cli.py --cache-dir data/intraday    # istoric lung din cache daily

Pentru fiecare factor (momentum, reversal, low_vol, resmom, amihud) afiseaza Sharpe
full-sample, Sharpe OUT-OF-SAMPLE si p-value (sign-flip) pe streamul de randamente
NETE long-short, apoi blend-ul sign-aware. NU este consiliere de investitii.
"""

import argparse

from markov.validation.tier2b import (blend_oos, evaluate_universe, factor_streams,
                                       load_universe, panel_from_cache, render_blend,
                                       render_xs)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validare factori cross-sectionali.")
    ap.add_argument("--universe", default="data/sp500.csv",
                    help="CSV panel long (date, close, volume, Name)")
    ap.add_argument("--cache-dir",
                    help="in loc de CSV: construieste panel-ul din cache-ul daily "
                         "(fereastra comuna, toate numele). Istoric mai lung.")
    ap.add_argument("--symbols",
                    help="cu --cache-dir: lista simboluri (implicit toate din cache)")
    ap.add_argument("--split", type=float, default=0.6,
                    help="fractia in-sample (restul = OOS)")
    ap.add_argument("--n-perm", type=int, default=2000,
                    help="permutari pentru p-value (sign-flip)")
    ap.add_argument("--no-blend", action="store_true",
                    help="sari peste blend-ul sign-aware")
    args = ap.parse_args(argv)

    if args.cache_dir:
        syms = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
                if args.symbols else None)
        P, V, dates, names = panel_from_cache(args.cache_dir, symbols=syms)
        span = f"{str(dates[0])[:10]}..{str(dates[-1])[:10]}, {len(dates)} zile"
        print(f"(panel din cache: {len(names)} nume, {span})\n")
    else:
        P, V, _dates = load_universe(args.universe)

    rows = evaluate_universe(P, V, split_frac=args.split, n_perm=args.n_perm)
    print(render_xs(rows, n_assets=P.shape[1]))
    if not args.no_blend:
        blend = blend_oos(factor_streams(P, V), split_frac=args.split,
                          n_perm=args.n_perm)
        print("\n" + render_blend(blend))


if __name__ == "__main__":
    main()
