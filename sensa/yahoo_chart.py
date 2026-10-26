"""Candles from Yahoo Finance's public chart endpoint (no key, no daily quota) for every chart timeframe.

Unofficial endpoint, personal / research use; sent with the same identifying User-Agent as the rest of the app."""

import json
import re
from datetime import datetime, timezone

from markov.data_providers import DataUnavailable

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={range}&interval={interval}"
_SYM = re.compile(r"^[A-Z0-9.\-]{1,10}$")
# timeframe -> (interval, range); 4h is built from hourly bars
_FRAMES = {"15m": ("15m", "1mo"), "30m": ("30m", "1mo"), "1h": ("60m", "3mo"), "4h": ("60m", "6mo"), "1day": ("1d", "2y")}


class YahooChart:
    def __init__(self, fetch):
        self.fetch = fetch

    def candles(self, symbol, tf):
        if tf not in _FRAMES:
            raise ValueError(f"bad timeframe {tf!r}")
        s = (symbol or "").upper()
        if not _SYM.match(s):
            raise ValueError("bad symbol")
        interval, rng = _FRAMES[tf]
        try:
            d = json.loads(self.fetch(URL.format(sym=s, range=rng, interval=interval)))["chart"]
        except (ValueError, KeyError, TypeError):
            raise DataUnavailable("chart data unavailable (unreadable response)") from None
        res = (d.get("result") or [None])[0]
        if not res:
            err = (d.get("error") or {}).get("description") or "no chart data"
            raise DataUnavailable(str(err)[:120])
        q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
        off = (res.get("meta") or {}).get("gmtoffset") or 0
        bars = []
        for i, t in enumerate(res.get("timestamp") or []):
            try:
                o, h, l, c = (q[k][i] for k in ("open", "high", "low", "close"))
            except (KeyError, IndexError):
                continue
            if None in (o, h, l, c):
                continue
            vol = (q.get("volume") or [0] * (i + 1))[i] or 0
            if tf != "1day" and not vol and o == h == l == c:
                continue                              # extended-hours placeholder, not a traded bar
            bars.append({"time": t, "open": float(o), "high": float(h), "low": float(l), "close": float(c),
                         "volume": float(vol), "_day": (t + off) // 86400})
        if tf == "4h":
            bars = _four_hour(bars)
        for b in bars:
            b.pop("_day", None)
            if tf == "1day":
                b["time"] = datetime.fromtimestamp(b["time"] + off, timezone.utc).strftime("%Y-%m-%d")
        return bars


def _four_hour(bars):
    out, day, chunk = [], None, []

    def flush():
        if chunk:
            out.append({"time": chunk[0]["time"], "open": chunk[0]["open"], "high": max(b["high"] for b in chunk),
                        "low": min(b["low"] for b in chunk), "close": chunk[-1]["close"],
                        "volume": sum(b["volume"] for b in chunk), "_day": chunk[0]["_day"]})
    for b in bars:
        if b["_day"] != day or len(chunk) == 4:
            flush()
            chunk, day = [], b["_day"]
        chunk.append(b)
    flush()
    return out
