"""Testeaza ONEST sistemul BUY-THE-DIP pe un watchlist: pragul `dip` ales pe
in-sample, performanta OUT-OF-SAMPLE, comparat cu buy-and-hold, + test pooled
pe tot portofoliul (rezolva testarea multipla).

    python dipbuy_cli.py --watchlist NVDA,AAPL,MSFT --universe data/sp500.csv

Sursa: --universe (CSV long OHLC) sau --data-dir (cache). NU consiliere de
investitii -- harness de verificare descriptiv.
"""

import argparse
import sys

import numpy as np
import pandas as pd

from markov.dipbuy import dipbuy_positions
from markov.intraday.bars import Bars
from markov.intraday.cache import read_bars
from markov.posscore import score_positions
from markov.trendpull_eval import bh_metrics, pooled_significance
from markov.wfselect import oos_streams

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


def _sh(v):
    return f"{v:+.2f}" if np.isfinite(v) else " n/a"


def run(symbols, data_dir, universe, cost_bps, dips, split, lookback, exit_ma, n_perm):
    cost = cost_bps / 1e4
    out = [DISCLAIMER, "",
           "=== BUY-THE-DIP (long-only) vs BUY&HOLD pe felia OOS ===",
           f"dips testati: {dips}  lookback={lookback}  exit_ma={exit_ma}  "
           f"split={split}  cost={cost_bps} bps", ""]
    streams = []
    posfn = lambda b, d: dipbuy_positions(b, dip=d, lookback=lookback, exit_ma=exit_ma)
    for sym in symbols:
        bars = _load_bars(sym.upper(), data_dir, universe)
        if bars is None or len(bars) < 120:
            out.append(f"  {sym:<6} (date insuficiente in setul nostru)")
            continue
        dip, pos, fwd = oos_streams(posfn, bars, dips, split=split, cost=cost)
        strat = score_positions(pos, fwd, cost=cost, n_perm=n_perm)
        bh = bh_metrics(fwd)
        edge = strat["sharpe"] - bh["bh_sharpe"]
        out.append(f"  {sym:<6} dip={dip:<4} | SISTEM net={strat['net_return']*100:+6.1f}% "
                   f"Sh={_sh(strat['sharpe'])} p={strat['p_value']:.3f} "
                   f"| B&H net={bh['bh_return']*100:+6.1f}% Sh={_sh(bh['bh_sharpe'])} "
                   f"| edge_Sh={_sh(edge)} in-mkt={float((pos>0).mean())*100:3.0f}%")
        streams.append((pos, fwd))
    if streams:
        pooled = pooled_significance(streams, cost=cost, n_perm=n_perm)
        out += ["", f"  POOLED (un singur test pe tot watchlist-ul): "
                f"net={pooled['net_return']*100:+.1f}%  Sh={_sh(pooled['sharpe'])}  "
                f"zile={pooled['n_days']}  p={pooled['p_value']:.3f}"]
    out += ["", "Citeste onest: 'edge_Sh' = Sharpe sistem - Sharpe B&H. POOLED"
            " p<0.05 = timing real dincolo de testarea multipla.", "", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Test walk-forward buy-the-dip.")
    ap.add_argument("--symbol")
    ap.add_argument("--watchlist")
    ap.add_argument("--data-dir")
    ap.add_argument("--universe")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--dips", default="0.1,0.15,0.2,0.3")
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--lookback", type=int, default=60)
    ap.add_argument("--exit-ma", type=int, default=20)
    ap.add_argument("--n-perm", type=int, default=1000)
    args = ap.parse_args(argv)
    syms = ([args.symbol] if args.symbol else
            [s for s in (args.watchlist or "").split(",") if s.strip()])
    if not syms:
        raise SystemExit("Da --symbol sau --watchlist.")
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    dips = [float(x) for x in args.dips.split(",") if x.strip()]
    print(run(syms, args.data_dir, args.universe, args.cost_bps, dips,
              args.split, args.lookback, args.exit_ma, args.n_perm))


if __name__ == "__main__":
    sys.exit(main())
