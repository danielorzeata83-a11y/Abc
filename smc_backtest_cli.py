"""Ruleaza harness-ul SMC (BOS + retest FVG) pe date REALE si arata, negru pe
alb, ce iese NET de costuri + p-value. Sweep de cost ca sa vezi pragul la care
regula moare.

    python smc_backtest_cli.py --symbol NVDA --universe data/sp500.csv
    python smc_backtest_cli.py --symbol AAPL --data-dir data/intraday --cost-bps 0,5,10,25

Sursa: --data-dir (cache daily/intraday backfilled) sau --universe (CSV long OHLC
cu coloanele date,open,high,low,close,volume,Name). NU consiliere de investitii.
"""

import argparse
import sys

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import read_bars
from markov.smc import backtest_smc

DISCLAIMER = "NU este consiliere de investitii. Harness de verificare descriptiv."


def _load_bars(symbol, data_dir, universe):
    if universe:
        raw = pd.read_csv(universe)
        g = raw[raw["Name"].astype(str) == str(symbol)].sort_values("date")
        if g.empty:
            raise SystemExit(f"{symbol} lipseste in {universe}")
        return Bars(pd.to_datetime(g["date"]).to_numpy(),
                    g["open"].to_numpy(float), g["high"].to_numpy(float),
                    g["low"].to_numpy(float), g["close"].to_numpy(float),
                    g.get("volume", pd.Series(np.ones(len(g)))).to_numpy(float))
    bars = read_bars(data_dir, symbol)
    if bars is None:
        raise SystemExit(f"{symbol} lipseste in cache {data_dir} (ruleaza backfill_cli).")
    return bars


def _fmt(r):
    sh = f"{r['sharpe']:+.2f}" if np.isfinite(r["sharpe"]) else "n/a"
    return (f"gross={r['gross_return']*100:+6.1f}%  net={r['net_return']*100:+6.1f}%  "
            f"Sharpe={sh}  maxDD={r['max_drawdown']*100:5.0f}%  "
            f"trades={r['n_trades']:4d}  p={r['p_value']:.3f}")


def run(symbol, data_dir, universe, costs_bps, k, timeout, ppy, n_perm):
    bars = _load_bars(symbol.upper(), data_dir, universe)
    out = [DISCLAIMER, "",
           f"=== SMC (BOS + retest FVG) pe {symbol.upper()} | {len(bars)} bare ===",
           "regula codificata MECANIC si CAUZAL (fara repaint). p<0.05 = timing"
           " improbabil sa fie noroc.", ""]
    for bps in costs_bps:
        r = backtest_smc(bars, cost=bps / 1e4, periods_per_year=ppy,
                         n_perm=n_perm, k=k, timeout=timeout)
        out.append(f"  cost={bps:>4.1f} bps : {_fmt(r)}")
    out += ["", "Citeste onest: daca net-ul devine negativ pe masura ce creste"
            " costul, edge-ul era inghitit de turnover (vezi discutia despre"
            " frecventa).", "", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backtest SMC net de costuri.")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--data-dir", help="cache backfilled")
    ap.add_argument("--universe", help="CSV long OHLC (ex. data/sp500.csv)")
    ap.add_argument("--cost-bps", default="0,5,10,25",
                    help="lista de costuri in bps pentru sweep (default 0,5,10,25)")
    ap.add_argument("--k", type=int, default=2, help="lookback pivot swing")
    ap.add_argument("--timeout", type=int, default=10, help="bare de asteptare retest")
    ap.add_argument("--ppy", type=int, default=252, help="perioade/an pt Sharpe")
    ap.add_argument("--n-perm", type=int, default=1000)
    args = ap.parse_args(argv)
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    costs = [float(x) for x in str(args.cost_bps).split(",") if x.strip() != ""]
    print(run(args.symbol, args.data_dir, args.universe, costs,
              args.k, args.timeout, args.ppy, args.n_perm))


if __name__ == "__main__":
    sys.exit(main())
