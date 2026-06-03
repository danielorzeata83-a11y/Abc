"""Backfill controlat al cache-ului 15m de la Alpha Vantage (free tier 25/zi).

Aduce, simbol cu simbol si luna cu luna, seriile de 15min in cache-ul local
(data/intraday/<SYMBOL>_15m.csv). Respecta limita free tier: ~5/min (pauza intre
apeluri) si se opreste ELEGANT cand AV raspunde cu throttle (limita zilnica atinsa),
ca sa poti relua a doua zi de unde a ramas (datele deja aduse sunt pastrate).

    export ALPHAVANTAGE_API_KEY=...
    python backfill_cli.py --symbols NVDA,AAPL --months 12      # 24 apeluri (2 zile pe free)
    python backfill_cli.py --symbols MSFT,AMD,TSLA --months 12  # restul, a doua zi

Cheia se ia din mediu (ALPHAVANTAGE_API_KEY), niciodata hardcodata sau logata.
NU este consiliere de investitii.
"""

import argparse
import os
import time

import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.alphavantage import get_intraday_provider
from markov.intraday.cache import (backfill_months, merge_bars, read_bars,
                                   write_bars)
from markov.intraday.service import Config


def run_backfill(symbols, months, data_dir, provider, now=None,
                 sleeper=time.sleep, sleep_s=13, log=print):
    """Aduce `months` luni de 15min pentru fiecare simbol. Pe throttle se opreste
    si intoarce numarul de apeluri reusite (datele aduse raman in cache)."""
    now = now or pd.Timestamp.utcnow()
    calls = 0
    for sym in symbols:
        for month in backfill_months(now, months):
            try:
                fresh = provider.fetch_month(sym, month)
            except DataUnavailable as exc:
                log(f"[{sym} {month}] throttle/indisponibil ({exc}); "
                    f"opresc dupa {calls} apeluri -- reia maine.")
                return calls
            old = read_bars(data_dir, sym)
            write_bars(data_dir, sym, merge_bars(old, fresh) if old else fresh)
            calls += 1
            log(f"[{sym} {month}] OK: {len(fresh)} bare 15m (apeluri={calls})")
            sleeper(sleep_s)            # <=5/min, prietenos cu free tier
    log(f"Gata: {calls} apeluri reusite.")
    return calls


def main(argv=None, provider=None, sleeper=time.sleep):
    ap = argparse.ArgumentParser(description="Backfill cache 15m de la Alpha Vantage.")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--months", type=int, default=12, help="cate luni in urma")
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else list(cfg.watchlist))
    data_dir = args.data_dir or cfg.data_dir

    if provider is None:
        key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
        if not key:
            raise SystemExit("Lipseste ALPHAVANTAGE_API_KEY in mediu.")
        provider = get_intraday_provider(f"av:{key}")

    run_backfill(symbols, args.months, data_dir, provider, sleeper=sleeper)


if __name__ == "__main__":
    main()
