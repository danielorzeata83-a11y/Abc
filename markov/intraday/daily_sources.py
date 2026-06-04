"""Surse daily gratis, cu istoric adanc -> Bars. urllib + numpy/pandas, fara dependinte.

Acelasi tipar ca markov.intraday.alphavantage (parsare pura + provider cu opener
injectabil pentru teste offline). Fiecare provider expune .fetch(symbol) -> Bars
zilnice, deci intra direct in backfill_cli.run_backfill_daily.

  - Stooq      : fara cheie, zeci de ani, CSV.            spec "stooq"
  - Yahoo      : fara cheie, istoric adanc, JSON chart.   spec "yahoo"
  - Twelve Data: cheie, 800 apeluri/zi free, JSON.        spec "td:<KEY>"

Cheile se iau din mediu, niciodata hardcodate sau logate. NU consiliere de investitii.
"""

import io
import json
import urllib.parse
import urllib.request
from urllib.error import URLError

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.bars import Bars

# User-Agent neutru: Yahoo/Stooq pot raspunde 429 la clientul default urllib.
_UA = {"User-Agent": "Mozilla/5.0 (compatible; markov-research/1.0)"}


def _bars_from_cols(ts, o, h, l, c, v):
    return Bars(np.asarray(ts, dtype="datetime64[ns]"),
                np.asarray(o, float), np.asarray(h, float),
                np.asarray(l, float), np.asarray(c, float),
                np.asarray(v, float))


def _get(opener, url, decode_json):
    try:
        with opener(urllib.request.Request(url, headers=_UA), timeout=30) as resp:
            raw = resp.read().decode()
    except URLError as e:
        raise DataUnavailable(f"sursa indisponibila: {e}")
    return json.loads(raw) if decode_json else raw


# --- Stooq -------------------------------------------------------------------

def parse_stooq_csv(text):
    """CSV Stooq (Date,Open,High,Low,Close,Volume; ascendent) -> Bars."""
    head = text.lstrip()[:40].upper()
    if head.startswith(("<", "EXCEEDED", "PRZEKROCZONY")) or "LIMIT" in head:
        raise DataUnavailable("Stooq rate-limit / IP blocat (raspuns non-CSV) -- "
                              "reia mai tarziu sau foloseste --source yahoo")
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise DataUnavailable("Stooq: raspuns non-CSV (probabil rate-limit/IP "
                              f"blocat) -- incearca --source yahoo. Detaliu: {e}")
    need = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if df.empty or not need <= set(df.columns):
        raise DataUnavailable("Stooq: fara date pentru simbol")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty:
        raise DataUnavailable("Stooq: serie goala")
    ts = pd.to_datetime(df["Date"]).to_numpy()
    return _bars_from_cols(ts, df["Open"], df["High"], df["Low"],
                           df["Close"], df["Volume"].fillna(0.0))


class StooqDailyProvider:
    BASE = "https://stooq.com/q/d/l/"

    def __init__(self, opener=None):
        self._opener = opener or urllib.request.urlopen

    def fetch(self, symbol):
        # Simbolurile US la Stooq au sufix .us (ex. nvda.us).
        s = symbol.lower()
        if "." not in s:
            s = f"{s}.us"
        url = f"{self.BASE}?{urllib.parse.urlencode({'s': s, 'i': 'd'})}"
        return parse_stooq_csv(_get(self._opener, url, decode_json=False))


# --- Yahoo Finance -----------------------------------------------------------

def parse_yahoo_chart(payload):
    """JSON v8 chart Yahoo -> Bars; randurile cu vreun OHLC null sunt sarite."""
    chart = payload.get("chart") if isinstance(payload, dict) else None
    if not isinstance(chart, dict) or chart.get("error") or not chart.get("result"):
        raise DataUnavailable(f"Yahoo: {(chart or {}).get('error', 'fara rezultat')}")
    res = chart["result"][0]
    ts_epoch = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    o, h, l, c, v = (q.get(k) or [] for k in ("open", "high", "low", "close", "volume"))
    rows = []
    for i, t in enumerate(ts_epoch):
        vals = (o[i], h[i], l[i], c[i])
        if any(x is None for x in vals):
            continue
        vol = v[i] if i < len(v) and v[i] is not None else 0.0
        rows.append((t, *vals, vol))
    if not rows:
        raise DataUnavailable("Yahoo: serie goala")
    cols = list(zip(*rows))
    ts = (np.asarray(cols[0], dtype="int64") * 1_000_000_000).astype("datetime64[ns]")
    return _bars_from_cols(ts, cols[1], cols[2], cols[3], cols[4], cols[5])


class YahooDailyProvider:
    BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"

    def __init__(self, opener=None, range_="max"):
        self._opener = opener or urllib.request.urlopen
        self.range_ = range_

    def fetch(self, symbol):
        params = urllib.parse.urlencode({"range": self.range_, "interval": "1d"})
        url = f"{self.BASE}{urllib.parse.quote(symbol)}?{params}"
        return parse_yahoo_chart(_get(self._opener, url, decode_json=True))


# --- Twelve Data -------------------------------------------------------------

def parse_twelvedata(payload):
    """JSON time_series Twelve Data (descendent) -> Bars sortat ascendent."""
    if not isinstance(payload, dict) or payload.get("status") == "error":
        msg = payload.get("message", "necunoscut") if isinstance(payload, dict) else "payload"
        raise DataUnavailable(f"Twelve Data: {msg}")
    values = payload.get("values")
    if not values:
        raise DataUnavailable("Twelve Data: fara valori")
    rows = [(pd.Timestamp(d["datetime"]), float(d["open"]), float(d["high"]),
             float(d["low"]), float(d["close"]), float(d.get("volume") or 0.0))
            for d in values]
    rows.sort(key=lambda r: r[0])
    cols = list(zip(*rows))
    return _bars_from_cols(cols[0], cols[1], cols[2], cols[3], cols[4], cols[5])


class TwelveDataDailyProvider:
    BASE = "https://api.twelvedata.com/time_series"

    def __init__(self, api_key, opener=None, outputsize=5000):
        self.api_key = api_key
        self._opener = opener or urllib.request.urlopen
        self.outputsize = outputsize

    def fetch(self, symbol):
        params = {"symbol": symbol, "interval": "1day",
                  "outputsize": self.outputsize, "apikey": self.api_key}
        url = f"{self.BASE}?{urllib.parse.urlencode(params)}"
        return parse_twelvedata(_get(self._opener, url, decode_json=True))


# --- dispatch unic -----------------------------------------------------------

def get_daily_source(spec, opener=None):
    """spec: 'stooq' | 'yahoo' | 'td:<KEY>' -> provider daily cu .fetch(symbol)."""
    if spec == "stooq":
        return StooqDailyProvider(opener)
    if spec == "yahoo":
        return YahooDailyProvider(opener)
    if spec.startswith("td:"):
        return TwelveDataDailyProvider(spec[3:], opener)
    raise ValueError(f"sursa daily necunoscuta: {spec!r}")
