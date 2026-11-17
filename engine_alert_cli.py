"""Raport zilnic al motorului (vol forecast + lead-lag) -> Telegram.

    export TELEGRAM_TOKEN=...      # de la @BotFather
    export TELEGRAM_CHAT_ID=...    # din telegram_chatid.py
    python engine_alert_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday

--dry-run tipareste mesajul fara sa-l trimita. NU este consiliere de investitii.
"""

import argparse
import os

import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.service import Config
from markov.telegram import send_message
from markov.validation.alert import build_from_cache


def main(argv=None, sender=send_message):
    ap = argparse.ArgumentParser(description="Raport motor -> Telegram.")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir")
    ap.add_argument("--bins", type=int, default=4)
    ap.add_argument("--lag", type=int, default=1)
    ap.add_argument("--token", default=os.environ.get("TELEGRAM_TOKEN"))
    ap.add_argument("--chat-id", default=os.environ.get("TELEGRAM_CHAT_ID"))
    ap.add_argument("--dry-run", action="store_true",
                    help="tipareste mesajul fara sa-l trimita")
    ap.add_argument("--asof", help="data raportului (YYYY-MM-DD); implicit azi")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else list(cfg.watchlist))
    data_dir = args.data_dir or cfg.data_dir
    asof = args.asof or pd.Timestamp.now().strftime("%Y-%m-%d")

    try:
        msg = build_from_cache(symbols, data_dir, asof, bins=args.bins, lag=args.lag)
    except DataUnavailable as e:
        raise SystemExit(
            f"Cache gol pentru {data_dir} ({e}). Populeaza-l intai (fara cheie API):\n"
            f"  python backfill_cli.py --source stooq --daily --symbols "
            f"{','.join(symbols)} --data-dir {data_dir}")

    if args.dry_run:
        print(msg)
        return
    if not args.token or not args.chat_id:
        raise SystemExit("Seteaza TELEGRAM_TOKEN si TELEGRAM_CHAT_ID (env sau "
                         "--token/--chat-id). Foloseste --dry-run pentru previzualizare.")
    resp = sender(args.token, args.chat_id, msg)
    print("Trimis." if resp.get("ok") else f"Eroare Telegram: {resp}")


if __name__ == "__main__":
    main()
