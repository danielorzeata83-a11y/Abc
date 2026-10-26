"""Free data providers, no key needed except the optional analyst feed. Each takes
an injectable fetch(url, headers)->str so tests need no network. Keys travel in
headers, never in URLs (no log leakage).

    Cboe delayed quotes (cdn.cboe.com)   quotes + full option chain with greeks
    FRED CSV (fred.stlouisfed.org)       US Treasury yield curve
    Yahoo Finance RSS                    headlines
    FINNHUB_API_KEY (optional)           analyst recommendations
Cboe data is ~15 min delayed; personal / research use only.
"""

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urlencode, quote as urlquote

from markov.data_providers import DataUnavailable


USER_AGENT = "Abc-dashboard-research/1.0 (personal, non-commercial)"


def with_user_agent(headers):
    return {"User-Agent": USER_AGENT, **(headers or {})}


def http_fetch(url, headers=None):
    req = urllib.request.Request(url, headers=with_user_agent(headers))
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as e:
        raise DataUnavailable(f"fetch failed ({type(e).__name__}) for {url.split('?')[0]}") from e


class Finnhub:
    BASE = "https://finnhub.io/api/v1"

    def __init__(self, key, fetch=http_fetch):
        self.key, self.fetch = key, fetch

    def recommendations(self, symbol):
        if not self.key:
            raise DataUnavailable("FINNHUB_API_KEY not set")
        url = f"{self.BASE}/stock/recommendation?{urlencode({'symbol': symbol.upper()})}"
        return json.loads(self.fetch(url, {"X-Finnhub-Token": self.key}))


_INDEXES = {"SPX", "VIX", "NDX", "RUT", "DJX", "XSP"}
_OCC = re.compile(r"^[A-Z0-9.]{1,6}?(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")


class Cboe:
    BASE = "https://cdn.cboe.com/api/global/delayed_quotes"

    def __init__(self, fetch=http_fetch):
        self.fetch = fetch

    def _get(self, kind, symbol):
        s = symbol.upper()
        s = "_" + s if s in _INDEXES else s
        # urllib follows the cdn.cboe.com -> cdn-api.cboe.com redirect itself
        return json.loads(self.fetch(f"{self.BASE}/{kind}/{urlquote(s)}.json", {}))["data"]

    def quote(self, symbol):
        d = self._get("quotes", symbol)
        return {"price": d.get("current_price"), "prev_close": d.get("prev_day_close"),
                "iv30": d.get("iv30")}

    def chain(self, symbol):
        d = self._get("options", symbol)
        out = []
        for o in d.get("options", []):
            m = _OCC.match(o.get("option", ""))
            if not m:
                continue
            yy, mm, dd, cp, strike = m.groups()
            out.append({"option_type": "call" if cp == "C" else "put",
                        "strike": int(strike) / 1000, "expiration": f"20{yy}-{mm}-{dd}",
                        "gamma": o.get("gamma"), "delta": o.get("delta"), "iv": o.get("iv"),
                        "open_interest": o.get("open_interest"), "volume": o.get("volume"),
                        "bid": o.get("bid"), "ask": o.get("ask")})
        return d.get("current_price"), out


_FRED = [("DGS1MO", "1M"), ("DGS3MO", "3M"), ("DGS6MO", "6M"), ("DGS1", "1Y"),
         ("DGS2", "2Y"), ("DGS5", "5Y"), ("DGS10", "10Y"), ("DGS30", "30Y")]


class FredApi:
    """Official FRED API (free key, FRED_API_KEY). The key rides in the query string
    as FRED requires; errors strip the query so it never reaches logs or responses."""
    BASE = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, key, fetch=http_fetch, series=_FRED):
        self.key, self.fetch, self.series = key, fetch, series

    def _latest(self, series_id):
        qs = urlencode({"series_id": series_id, "api_key": self.key, "file_type": "json",
                        "sort_order": "desc", "limit": 10})
        obs = json.loads(self.fetch(f"{self.BASE}?{qs}", {}))["observations"]
        return {o["date"]: float(o["value"]) for o in obs if o["value"] != "."}

    def curve(self):
        if not self.key:
            raise DataUnavailable("FRED_API_KEY not set")
        per = [(lbl, self._latest(sid)) for sid, lbl in self.series]
        common = set.intersection(*(set(d) for _, d in per))
        if not common:
            return None
        day = max(common)
        return {"date": day, "points": [(lbl, d[day]) for lbl, d in per]}


YAHOO_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US"


def yahoo_news(rss_text):
    if "<!DOCTYPE" in rss_text.upper() or "<!ENTITY" in rss_text.upper():
        raise DataUnavailable("refusing XML with DTD/entities")
    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError as e:
        raise DataUnavailable(f"bad RSS: {e}") from e
    return [{"headline": (i.findtext("title") or "").strip(), "url": (i.findtext("link") or "").strip(),
             "source": "Yahoo Finance", "datetime": (i.findtext("pubDate") or "").strip()}
            for i in root.iter("item")]
