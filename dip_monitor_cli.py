"""Monitor DESCRIPTIV de watchlist pentru regula dip-adanc: unde sta fiecare nume
fata de maximele lui. NU semnal de cumparare -- harta, nu buton.

    python dip_monitor_cli.py --watchlist NVDA,AAPL,MSFT --universe data/sp500.csv
    python dip_monitor_cli.py --price-csv data/btc.csv:time:PriceUSD --name BTC

NU consiliere de investitii -- artefact de cercetare descriptiv.
"""

import argparse
import sys

import numpy as np
import pandas as pd

from markov.dipmonitor import dip_status
from markov.intraday.cache import read_bars
from markov.intraday.price_series import load_price_series

DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare descriptiv."


def _closes(symbol, data_dir, universe):
    if universe:
        raw = pd.read_csv(universe)
        g = raw[raw["Name"].astype(str) == str(symbol)].sort_values("date")
        return g["close"].to_numpy(dtype=float) if not g.empty else None
    bars = read_bars(data_dir, symbol)
    return np.asarray(bars.close, dtype=float) if bars is not None else None


def run(items, lookback, dip, exit_ma):
    out = [DISCLAIMER, "",
           f"=== MONITOR DIP-ADANC (lookback={lookback}z, prag={dip*100:.0f}%) ===",
           "Descriptiv: unde sta fiecare nume fata de maximul recent. Regula a fost",
           "FRANA DE RISC pe BTC (vezi BEARTEST_FINDINGS), nu accelerator de profit.",
           "",
           f"  {'nume':<8} {'pret':>10} {'maxim':>10} {'drawdown':>9} {'stare':<40}"]
    for name, close in items:
        if close is None or len(close) < lookback + 2:
            out.append(f"  {name:<8} (date insuficiente)")
            continue
        s = dip_status(close, lookback=lookback, dip=dip, exit_ma=exit_ma)
        extra = "" if s["in_deep_dip"] else f"  (mai cade {abs(s['to_threshold'])*100:.0f}% pana la prag)"
        out.append(f"  {name:<8} {s['price']:>10.2f} {s['high']:>10.2f} "
                   f"{s['drawdown']*100:>+8.0f}% {s['label']:<40}{extra}")
    out += ["", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Monitor descriptiv dip-adanc.")
    ap.add_argument("--watchlist")
    ap.add_argument("--data-dir")
    ap.add_argument("--universe")
    ap.add_argument("--price-csv", help="cale:datecol:pricecol (ex. data/btc.csv:time:PriceUSD)")
    ap.add_argument("--name", default="ASSET", help="nume pentru --price-csv")
    ap.add_argument("--lookback", type=int, default=60)
    ap.add_argument("--dip", type=float, default=0.4)
    ap.add_argument("--exit-ma", type=int, default=20)
    args = ap.parse_args(argv)

    items = []
    if args.price_csv:
        path, dc, pc = args.price_csv.split(":")
        items.append((args.name, np.asarray(load_price_series(path, dc, pc).close, dtype=float)))
    else:
        syms = [s for s in (args.watchlist or "").split(",") if s.strip()]
        if not syms:
            raise SystemExit("Da --watchlist (+ --universe/--data-dir) sau --price-csv.")
        if not args.data_dir and not args.universe:
            raise SystemExit("Da --data-dir SAU --universe.")
        items = [(s.upper(), _closes(s.upper(), args.data_dir, args.universe)) for s in syms]
    print(run(items, args.lookback, args.dip, args.exit_ma))


if __name__ == "__main__":
    sys.exit(main())
