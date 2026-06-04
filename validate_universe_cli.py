"""CLI #3: ruleaza factorii TIME-SERIES (tier2) pe un UNIVERS larg, nu doar
cateva nume. Pooling-ul IC pe sute de simboluri arata daca edge-ul slab de pe
5 nume devine semnificativ statistic pe mai multe active.

Construieste un cache temporar din panel-ul long (date, ohlcv, Name), apoi
ruleaza acelasi motor A->E ca validate_cli.

    python validate_universe_cli.py --universe data/sp500.csv --indicators tier2

NU este consiliere de investitii.
"""

import argparse
import tempfile

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import tier1, tier2
from markov.validation.report import run_validation

_TIERS = {"tier1": tier1.INDICATORS, "tier2": tier2.INDICATORS,
          "all": {**tier1.INDICATORS, **tier2.INDICATORS}}


def cache_from_long_csv(csv_path, cache_dir, min_obs=200):
    """Panel long (date, ohlcv, Name) -> scrie Bars/simbol in cache_dir.
    Pastreaza doar numele cu >= min_obs bare. Intoarce lista simbolurilor scrise."""
    raw = pd.read_csv(csv_path)
    ts = pd.to_datetime(raw["date"]).to_numpy()
    written = []
    for name, g in raw.groupby("Name"):
        g = g.sort_values("date")
        if len(g) < min_obs:
            continue
        t = pd.to_datetime(g["date"]).to_numpy()
        c = g["close"].to_numpy(dtype=float)
        o = g["open"].to_numpy(dtype=float) if "open" in g else c
        h = g["high"].to_numpy(dtype=float) if "high" in g else c
        lo = g["low"].to_numpy(dtype=float) if "low" in g else c
        v = g["volume"].to_numpy(dtype=float) if "volume" in g else np.zeros(len(c))
        write_bars(cache_dir, str(name), Bars(t, o, h, lo, c, v))
        written.append(str(name))
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validare time-series pe univers larg.")
    ap.add_argument("--universe", default="data/sp500.csv")
    ap.add_argument("--indicators", default="tier2", choices=list(_TIERS))
    ap.add_argument("--horizons", default="1,5,21")
    ap.add_argument("--target", default="return", choices=["return", "vol"])
    ap.add_argument("--min-obs", type=int, default=200)
    args = ap.parse_args(argv)

    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())
    with tempfile.TemporaryDirectory() as d:
        symbols = cache_from_long_csv(args.universe, d, min_obs=args.min_obs)
        if not symbols:
            raise SystemExit(f"Niciun simbol cu >= {args.min_obs} bare in {args.universe}")
        rep = run_validation(symbols, d, _TIERS[args.indicators],
                             horizons=horizons, target=args.target)
        print(f"(univers: {len(symbols)} simboluri)\n")
        print(rep.render_text())


if __name__ == "__main__":
    main()
