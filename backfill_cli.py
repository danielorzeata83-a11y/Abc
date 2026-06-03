"""Backfill controlat al cache-ului de la Alpha Vantage (free tier 25/zi).

Doua moduri:
  - DAILY (recomandat, --daily): TIME_SERIES_DAILY, outputsize=full -> 20+ ani de
    bare zilnice intr-UN SINGUR apel/simbol. Gratis. Exact granularitatea ceruta de
    motorul de validare (orizonturi 1/5/21 zile).
  - 15min (implicit): TIME_SERIES_INTRADAY luna cu luna. ATENTIE: parametrul `month`
    a devenit endpoint PREMIUM la Alpha Vantage -- pe cheie free pica imediat.

    export ALPHAVANTAGE_API_KEY=...
    python backfill_cli.py --daily --symbols NVDA,AAPL,MSFT,AMD,TSLA   # 5 apeluri, gratis
    python backfill_cli.py --symbols NVDA,AAPL --months 12             # 15m (necesita premium)

Cheia se ia din mediu (ALPHAVANTAGE_API_KEY), niciodata hardcodata sau logata.
NU este consiliere de investitii.
"""

import argparse
import os
import time

import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.alphavantage import (get_daily_provider,
                                          get_intraday_provider)
from markov.intraday.cache import (backfill_months, merge_bars, read_bars,
                                   write_bars)
from markov.intraday.service import Config


def run_backfill(symbols, months, data_dir, provider, now=None,
                 sleeper=time.sleep, sleep_s=13, log=print):
    """Aduce `months` luni de 15min pentru fiecare simbol. Pe throttle se opreste
    si intoarce numarul de apeluri reusite (datele aduse raman in cache)."""
    now = now or pd.Timestamp.now("UTC")
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


def run_backfill_daily(symbols, data_dir, provider, sleeper=time.sleep,
                       sleep_s=13, log=print):
    """Aduce istoricul daily complet (un apel/simbol). Pe throttle se opreste si
    intoarce numarul de apeluri reusite (datele aduse raman in cache)."""
    calls = 0
    for sym in symbols:
        try:
            fresh = provider.fetch(sym)
        except DataUnavailable as exc:
            log(f"[{sym}] throttle/indisponibil ({exc}); "
                f"opresc dupa {calls} apeluri -- reia maine.")
            return calls
        old = read_bars(data_dir, sym)
        write_bars(data_dir, sym, merge_bars(old, fresh) if old else fresh)
        calls += 1
        log(f"[{sym}] OK: {len(fresh)} bare daily (apeluri={calls})")
        sleeper(sleep_s)               # <=5/min, prietenos cu free tier
    log(f"Gata: {calls} apeluri reusite.")
    return calls


def main(argv=None, provider=None, sleeper=time.sleep):
    ap = argparse.ArgumentParser(description="Backfill cache de la Alpha Vantage.")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--months", type=int, default=12, help="cate luni in urma (mod 15m)")
    ap.add_argument("--daily", action="store_true",
                    help="istoric daily complet (free, 1 apel/simbol) -- recomandat")
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
        spec = f"av:{key}"
        provider = get_daily_provider(spec) if args.daily else get_intraday_provider(spec)

    if args.daily:
        run_backfill_daily(symbols, data_dir, provider, sleeper=sleeper)
    else:
        run_backfill(symbols, args.months, data_dir, provider, sleeper=sleeper)


if __name__ == "__main__":
    main()
