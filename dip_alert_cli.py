"""Alerta dip-adanc -> Telegram. LINISTITA: trimite doar cand un nume din
watchlist intra in zona de dip adanc (sau aproape). Descriptiv, NU semnal.

    export TELEGRAM_TOKEN=...      # de la @BotFather
    export TELEGRAM_CHAT_ID=...    # din telegram_chatid.py
    python dip_alert_cli.py --watchlist NVDA,AAPL,MSFT --universe data/sp500.csv
    python dip_alert_cli.py --price-csv data/btc.csv:time:PriceUSD --name BTC --dry-run

--dry-run tipareste fara sa trimita. --quiet-if-empty nu trimite cand nu e nimic.
NU este consiliere de investitii.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

from markov.dipmonitor import dip_alert
from markov.intraday.cache import read_bars
from markov.intraday.price_series import load_price_series
from markov.telegram import send_message


def _closes(symbol, data_dir, universe):
    if universe:
        raw = pd.read_csv(universe)
        g = raw[raw["Name"].astype(str) == str(symbol)].sort_values("date")
        return g["close"].to_numpy(dtype=float) if not g.empty else None
    bars = read_bars(data_dir, symbol)
    return np.asarray(bars.close, dtype=float) if bars is not None else None


def _items(args):
    if args.price_csv:
        path, dc, pc = args.price_csv.split(":")
        return [(args.name, np.asarray(load_price_series(path, dc, pc).close, dtype=float))]
    syms = [s for s in (args.watchlist or "").split(",") if s.strip()]
    if not syms:
        raise SystemExit("Da --watchlist (+ --universe/--data-dir) sau --price-csv.")
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    return [(s.upper(), _closes(s.upper(), args.data_dir, args.universe)) for s in syms]


def main(argv=None, sender=send_message):
    ap = argparse.ArgumentParser(description="Alerta dip-adanc -> Telegram.")
    ap.add_argument("--watchlist")
    ap.add_argument("--data-dir")
    ap.add_argument("--universe")
    ap.add_argument("--price-csv", help="cale:datecol:pricecol")
    ap.add_argument("--name", default="ASSET")
    ap.add_argument("--asof", default="")
    ap.add_argument("--lookback", type=int, default=60)
    ap.add_argument("--dip", type=float, default=0.4)
    ap.add_argument("--exit-ma", type=int, default=20)
    ap.add_argument("--near", type=float, default=0.05)
    ap.add_argument("--token", default=os.environ.get("TELEGRAM_TOKEN"))
    ap.add_argument("--chat-id", default=os.environ.get("TELEGRAM_CHAT_ID"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet-if-empty", action="store_true",
                    help="nu trimite (si nu tipareste) cand nu e nimic in zona")
    args = ap.parse_args(argv)

    alert = dip_alert(_items(args), asof=args.asof, lookback=args.lookback,
                      dip=args.dip, exit_ma=args.exit_ma, near=args.near)
    if args.quiet_if_empty and not alert["active"]:
        return 0
    if args.dry_run:
        print(alert["text"])
        return 0
    if not args.token or not args.chat_id:
        raise SystemExit("Seteaza TELEGRAM_TOKEN si TELEGRAM_CHAT_ID (env sau "
                         "--token/--chat-id). Foloseste --dry-run pentru previzualizare.")
    sender(args.token, args.chat_id, alert["text"])
    print("Trimis." if alert["active"] else "Trimis (linistit).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
