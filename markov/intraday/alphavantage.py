"""Alpha Vantage intraday (15min) provider -> Bars. urllib + json only.

Mirrors markov.fundamentals_provider (spec 'av:<KEY>') and markov.telegram
(injectable opener for offline tests). One AV call per month
(TIME_SERIES_INTRADAY, interval=15min, outputsize=full, month=YYYY-MM).
"""

import json
import urllib.parse
import urllib.request
from urllib.error import URLError

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.bars import Bars

_TS_KEY = "Time Series (15min)"
_TS_DAILY_KEY = "Time Series (Daily)"


def _parse_series(payload, ts_key, what):
    if not isinstance(payload, dict):
        raise DataUnavailable("unexpected Alpha Vantage payload")
    for k in ("Note", "Information", "Error Message"):
        if k in payload:
            raise DataUnavailable(f"Alpha Vantage: {payload[k]}")
    series = payload.get(ts_key)
    if not series:
        raise DataUnavailable(f"no {what} series in payload")
    rows = []
    for ts, bar in series.items():
        rows.append((pd.Timestamp(ts), float(bar["1. open"]), float(bar["2. high"]),
                     float(bar["3. low"]), float(bar["4. close"]), float(bar["5. volume"])))
    rows.sort(key=lambda r: r[0])
    cols = list(zip(*rows))
    return Bars(np.array(cols[0], dtype="datetime64[ns]"),
                np.array(cols[1], float), np.array(cols[2], float),
                np.array(cols[3], float), np.array(cols[4], float),
                np.array(cols[5], float))


def parse_av_daily(payload):
    """Parse TIME_SERIES_DAILY (free tier, istoric adanc) -> Bars zilnice."""
    return _parse_series(payload, _TS_DAILY_KEY, "daily")


def parse_av_intraday(payload):
    if not isinstance(payload, dict):
        raise DataUnavailable("unexpected Alpha Vantage payload")
    for k in ("Note", "Information", "Error Message"):
        if k in payload:
            raise DataUnavailable(f"Alpha Vantage: {payload[k]}")
    series = payload.get(_TS_KEY)
    if not series:
        raise DataUnavailable("no intraday series in payload")
    rows = []
    for ts, bar in series.items():
        rows.append((pd.Timestamp(ts), float(bar["1. open"]), float(bar["2. high"]),
                     float(bar["3. low"]), float(bar["4. close"]), float(bar["5. volume"])))
    rows.sort(key=lambda r: r[0])
    cols = list(zip(*rows))
    return Bars(np.array(cols[0], dtype="datetime64[ns]"),
                np.array(cols[1], float), np.array(cols[2], float),
                np.array(cols[3], float), np.array(cols[4], float),
                np.array(cols[5], float))


class AlphaVantageIntradayProvider:
    BASE = "https://www.alphavantage.co/query"

    def __init__(self, api_key, opener=None):
        self.api_key = api_key
        self._opener = opener or urllib.request.urlopen

    def fetch_month(self, symbol, month):
        params = {"function": "TIME_SERIES_INTRADAY", "symbol": symbol,
                  "interval": "15min", "outputsize": "full", "month": month,
                  "apikey": self.api_key}
        url = f"{self.BASE}?{urllib.parse.urlencode(params)}"
        try:
            with self._opener(urllib.request.Request(url), timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except URLError as e:
            raise DataUnavailable(f"Alpha Vantage unreachable: {e}")
        return parse_av_intraday(payload)


class AlphaVantageDailyProvider:
    """Istoric daily complet intr-un singur apel (free tier: TIME_SERIES_DAILY,
    outputsize=full -> 20+ ani). Exact granularitatea ceruta de motorul de validare."""
    BASE = "https://www.alphavantage.co/query"

    def __init__(self, api_key, opener=None):
        self.api_key = api_key
        self._opener = opener or urllib.request.urlopen

    def fetch(self, symbol):
        params = {"function": "TIME_SERIES_DAILY", "symbol": symbol,
                  "outputsize": "full", "apikey": self.api_key}
        url = f"{self.BASE}?{urllib.parse.urlencode(params)}"
        try:
            with self._opener(urllib.request.Request(url), timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except URLError as e:
            raise DataUnavailable(f"Alpha Vantage unreachable: {e}")
        return parse_av_daily(payload)


def get_intraday_provider(spec, opener=None):
    if spec.startswith("av:"):
        return AlphaVantageIntradayProvider(spec[3:], opener)
    raise ValueError(f"unknown intraday provider spec: {spec!r}")


def get_daily_provider(spec, opener=None):
    if spec.startswith("av:"):
        return AlphaVantageDailyProvider(spec[3:], opener)
    raise ValueError(f"unknown daily provider spec: {spec!r}")
