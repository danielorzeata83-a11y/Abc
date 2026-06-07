"""Testeaza buy-the-dip pe ISTORIC LUNG care traverseaza crize (petrol 2008/2020,
BTC 2018/2022). Split 0.5 => felia OOS contine crahurile. Compara sistemul cu
buy-and-hold pe ACEEASI felie: net SI max drawdown (rezista cand activul cade?).

    python longtest_cli.py

NU consiliere de investitii -- harness de verificare descriptiv.
"""

import sys

import numpy as np

from markov.dipbuy import dipbuy_positions
from markov.intraday.price_series import load_price_series
from markov.posscore import score_positions
from markov.tradestats import trade_stats
from markov.trendpull_eval import bh_metrics
from markov.wfselect import oos_streams

DISCLAIMER = "NU este consiliere de investitii. Harness de verificare descriptiv."

ASSETS = [
    ("WTI  ", "data/wti.csv", "Date", "Price"),
    ("BRENT", "data/brent.csv", "Date", "Price"),
    ("BTC  ", "data/btc.csv", "time", "PriceUSD"),
]
DIPS = [0.1, 0.15, 0.2, 0.3, 0.4]


def _pf(v):
    return "inf " if v == float("inf") else (f"{v:.2f}" if np.isfinite(v) else "n/a")


def run(assets=ASSETS, dips=DIPS, split=0.5, cost_bps=5.0, n_perm=1000):
    cost = cost_bps / 1e4
    posfn = lambda b, d: dipbuy_positions(b, dip=d, lookback=60, exit_ma=20)
    out = [DISCLAIMER, "",
           "=== BUY-THE-DIP pe ISTORIC LUNG cu crize (OOS = a doua jumatate) ===",
           f"dips: {dips}  split={split}  cost={cost_bps} bps", "",
           f"  {'activ':<6} {'dip':>4} {'trades':>6} {'win%':>5} {'PF':>6} "
           f"{'exp/tr':>7} {'SIS net':>8} {'SIS DD':>7} {'B&H net':>9} "
           f"{'B&H DD':>7} {'p':>6}"]
    for name, csv, dc, pc in assets:
        bars = load_price_series(csv, dc, pc)
        if (np.asarray(bars.close) <= 0).any():
            out.append(f"  {name:<6} INVALID: pret <=0 in serie (ex. petrol 2020 "
                       "negativ) -> randamentele explodeaza, backtest fara sens.")
            continue
        dip, pos, fwd = oos_streams(posfn, bars, dips, split=split, cost=cost)
        s = trade_stats(pos, fwd, cost=cost)
        bh = bh_metrics(fwd)
        p = score_positions(pos, fwd, cost=cost, n_perm=n_perm)["p_value"]
        yrs = (np.datetime64(bars.timestamps[-1]) - np.datetime64(bars.timestamps[0])
               ) / np.timedelta64(365, "D")
        out.append(f"  {name:<6} {dip:>4} {s['n_trades']:>6} "
                   f"{s['win_rate']*100:>4.0f}% {_pf(s['profit_factor']):>6} "
                   f"{s['expectancy']*100:>+6.2f}% {s['net_return']*100:>+7.0f}% "
                   f"{s['max_drawdown']*100:>6.0f}% {bh['bh_return']*100:>+8.0f}% "
                   f"{bh['bh_max_drawdown']*100:>6.0f}% {p:>6.3f}  ({yrs:.0f}a)")
    out += ["", "SIS DD vs B&H DD = cat te-a protejat sistemul in crah (mai mic =",
            "mai bine). p<0.05 = timing real, nu doar drift. PF>1 = profitabil.",
            "", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    print(run())


if __name__ == "__main__":
    sys.exit(main())
