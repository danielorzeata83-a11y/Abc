"""Testeaza sistemul TREND-PULLBACK pe un watchlist, ONEST: pentru fiecare nume
alege multiplicatorul ATR pe felia in-sample si raporteaza OUT-OF-SAMPLE (cifra
in care ai voie sa crezi) + p-value prin permutare.

    python trendpull_cli.py --watchlist NVDA,AAPL,MSFT,AMD,TSLA --universe data/sp500.csv
    python trendpull_cli.py --symbol NVDA --data-dir data/intraday --cost-bps 5

Sursa: --universe (CSV long OHLC) sau --data-dir (cache). NU consiliere de
investitii -- harness de verificare descriptiv.
"""

import argparse
import sys

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import read_bars
from markov.trendpull import walk_forward_select

DISCLAIMER = "NU este consiliere de investitii. Harness de verificare descriptiv."


def _load_bars(symbol, data_dir, universe):
    if universe:
        raw = pd.read_csv(universe)
        g = raw[raw["Name"].astype(str) == str(symbol)].sort_values("date")
        if g.empty:
            return None
        return Bars(pd.to_datetime(g["date"]).to_numpy(),
                    g["open"].to_numpy(float), g["high"].to_numpy(float),
                    g["low"].to_numpy(float), g["close"].to_numpy(float),
                    g.get("volume", pd.Series(np.ones(len(g)))).to_numpy(float))
    return read_bars(data_dir, symbol)


def _row(sym, r):
    o = r["oos"]
    sh = f"{o['sharpe']:+.2f}" if np.isfinite(o["sharpe"]) else " n/a"
    return (f"  {sym:<6} mult={r['chosen_mult']:<3} | OOS: "
            f"net={o['net_return']*100:+6.1f}%  Sharpe={sh}  "
            f"maxDD={o['max_drawdown']*100:5.0f}%  trades={o['n_trades']:3d}  "
            f"p={o['p_value']:.3f}")


def run(symbols, data_dir, universe, cost_bps, mults, split, n_perm, **rule_kw):
    out = [DISCLAIMER, "",
           "=== TREND-PULLBACK (long-only) | walk-forward (in-sample alege mult,"
           " OOS = verdict) ===",
           f"mults testati: {list(mults)}  split={split}  cost={cost_bps} bps", ""]
    for sym in symbols:
        bars = _load_bars(sym.upper(), data_dir, universe)
        if bars is None or len(bars) < 120:
            out.append(f"  {sym:<6} (date insuficiente)")
            continue
        r = walk_forward_select(bars, mults=mults, split=split,
                                cost=cost_bps / 1e4, n_perm=n_perm, **rule_kw)
        out.append(_row(sym.upper(), r))
    out += ["", "Citeste onest: conteaza coloana OOS. p>=0.05 => timing"
            " nedistins de noroc. Numarul de trade-uri OOS ~ trenduri prinse.",
            "", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Test walk-forward trend-pullback.")
    ap.add_argument("--symbol")
    ap.add_argument("--watchlist", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir")
    ap.add_argument("--universe", help="CSV long OHLC (ex. data/sp500.csv)")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--mults", default="2.0,2.5,3.0,3.5")
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--ma-window", type=int, default=50)
    ap.add_argument("--slope-lookback", type=int, default=10)
    ap.add_argument("--atr-period", type=int, default=22)
    ap.add_argument("--n-perm", type=int, default=1000)
    args = ap.parse_args(argv)
    syms = ([args.symbol] if args.symbol else
            [s for s in (args.watchlist or "").split(",") if s.strip()])
    if not syms:
        raise SystemExit("Da --symbol sau --watchlist.")
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    mults = tuple(float(x) for x in args.mults.split(",") if x.strip())
    print(run(syms, args.data_dir, args.universe, args.cost_bps, mults,
              args.split, args.n_perm, ma_window=args.ma_window,
              slope_lookback=args.slope_lookback, atr_period=args.atr_period))


if __name__ == "__main__":
    sys.exit(main())
