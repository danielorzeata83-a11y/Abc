"""Raport de TRADER pentru un sistem (trend-pullback sau buy-the-dip) pe un
watchlist: win-rate, profit-factor, expectancy, net, max drawdown -- ce conta
cand scopul e "tranzactii cu profit", nu "bate buy-and-hold". p-value ramane
doar garda de onestitate (timing real vs drift de piata).

    python trade_report_cli.py --system trend --watchlist NVDA,AAPL --universe data/sp500.csv
    python trade_report_cli.py --system dip --watchlist NVDA,AAPL --universe data/sp500.csv

NU consiliere de investitii -- harness de verificare descriptiv.
"""

import argparse
import sys

import numpy as np
import pandas as pd

from markov.dipbuy import dipbuy_positions
from markov.intraday.bars import Bars
from markov.intraday.cache import read_bars
from markov.posscore import score_positions
from markov.tradestats import trade_stats
from markov.trendpull import trendpull_positions
from markov.trendpull_eval import pooled_significance
from markov.wfselect import oos_streams

DISCLAIMER = "NU este consiliere de investitii. Harness de verificare descriptiv."

SYSTEMS = {
    "trend": (lambda b, v: trendpull_positions(b, atr_mult=v),
              [2.0, 2.5, 3.0, 3.5], "atr_mult"),
    "dip": (lambda b, v: dipbuy_positions(b, dip=v),
            [0.1, 0.15, 0.2, 0.3], "dip"),
}


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


def _pf(v):
    return "inf " if v == float("inf") else (f"{v:.2f}" if np.isfinite(v) else "n/a")


def run(system, symbols, data_dir, universe, cost_bps, split, n_perm):
    posfn, grid, pname = SYSTEMS[system]
    cost = cost_bps / 1e4
    out = [DISCLAIMER, "",
           f"=== RAPORT TRADER: sistem '{system}' ({pname} ales walk-forward) ===",
           f"OOS | cost={cost_bps} bps | split={split}", "",
           f"  {'nume':<6} {'trades':>6} {'win%':>6} {'PF':>6} {'avgW':>7} "
           f"{'avgL':>7} {'net':>8} {'maxDD':>7} {'p':>6}"]
    streams = []
    for sym in symbols:
        bars = _load_bars(sym.upper(), data_dir, universe)
        if bars is None or len(bars) < 120:
            out.append(f"  {sym:<6} (date insuficiente)")
            continue
        _, pos, fwd = oos_streams(posfn, bars, grid, split=split, cost=cost)
        s = trade_stats(pos, fwd, cost=cost)
        p = score_positions(pos, fwd, cost=cost, n_perm=n_perm)["p_value"]
        if s["n_trades"] == 0:
            out.append(f"  {sym:<6} (0 tranzactii OOS)")
            continue
        out.append(f"  {sym.upper():<6} {s['n_trades']:>6} "
                   f"{s['win_rate']*100:>5.0f}% {_pf(s['profit_factor']):>6} "
                   f"{s['avg_win']*100:>6.1f}% {s['avg_loss']*100:>6.1f}% "
                   f"{s['net_return']*100:>+7.1f}% {s['max_drawdown']*100:>6.0f}% "
                   f"{p:>6.3f}")
        streams.append((pos, fwd))
    if streams:
        pl = pooled_significance(streams, cost=cost, n_perm=n_perm)
        ps = trade_stats(np.concatenate([s[0] for s in streams]),
                         np.concatenate([s[1] for s in streams]), cost=cost)
        out += ["", f"  POOLED  trades={ps['n_trades']}  win={ps['win_rate']*100:.0f}%"
                f"  PF={_pf(ps['profit_factor'])}  expectancy={ps['expectancy']*100:+.2f}%/trade"
                f"  net={ps['net_return']*100:+.1f}%  maxDD={ps['max_drawdown']*100:.0f}%"
                f"  p={pl['p_value']:.3f}"]
    out += ["", "PF>1 = profitabil. expectancy = castig mediu pe tranzactie (net).",
            "p<0.05 = timing real, nu doar drift de piata (garda de onestitate).",
            "", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Raport de trader pentru un sistem.")
    ap.add_argument("--system", choices=sorted(SYSTEMS), required=True)
    ap.add_argument("--symbol")
    ap.add_argument("--watchlist")
    ap.add_argument("--data-dir")
    ap.add_argument("--universe")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--n-perm", type=int, default=1000)
    args = ap.parse_args(argv)
    syms = ([args.symbol] if args.symbol else
            [s for s in (args.watchlist or "").split(",") if s.strip()])
    if not syms:
        raise SystemExit("Da --symbol sau --watchlist.")
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    print(run(args.system, syms, args.data_dir, args.universe, args.cost_bps,
              args.split, args.n_perm))


if __name__ == "__main__":
    sys.exit(main())
