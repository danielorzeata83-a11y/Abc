"""Free-tier data providers. Each takes an injectable fetch(url, headers)->str so
tests need no network. Keys travel in headers, never in URLs (no log leakage).

    FINNHUB_API_KEY   finnhub.io          quotes, news, analyst recommendations
    TRADIER_TOKEN     sandbox.tradier.com options chain + greeks (delayed, free)
    (none)            home.treasury.gov   daily yield curve
"""

import csv
import io
import json
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urlencode

from markov.data_providers import DataUnavailable


def http_fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as e:
        raise DataUnavailable(f"fetch failed ({type(e).__name__}) for {url.split('?')[0]}") from e


class Finnhub:
    BASE = "https://finnhub.io/api/v1"

    def __init__(self, key, fetch=http_fetch):
        self.key, self.fetch = key, fetch

    def _get(self, path, **params):
        if not self.key:
            raise DataUnavailable("FINNHUB_API_KEY not set")
        url = f"{self.BASE}/{path}?{urlencode(params)}"
        return json.loads(self.fetch(url, {"X-Finnhub-Token": self.key}))

    def quote(self, symbol):
        d = self._get("quote", symbol=symbol.upper())
        return {"price": d.get("c"), "prev_close": d.get("pc")}

    def recommendations(self, symbol):
        return self._get("stock/recommendation", symbol=symbol.upper())

    def news(self, symbol=None):
        if symbol:
            return self._get("company-news", symbol=symbol.upper())
        return self._get("news", category="general")


class TradierSandbox:
    BASE = "https://sandbox.tradier.com/v1"

    def __init__(self, token, fetch=http_fetch):
        self.token, self.fetch = token, fetch

    def _get(self, path, **params):
        if not self.token:
            raise DataUnavailable("TRADIER_TOKEN not set")
        url = f"{self.BASE}/{path}?{urlencode(params)}"
        return json.loads(self.fetch(url, {"Authorization": f"Bearer {self.token}",
                                           "Accept": "application/json"}))

    def expirations(self, symbol):
        d = (self._get("markets/options/expirations", symbol=symbol.upper()) or {})
        dates = (d.get("expirations") or {}).get("date") or []
        return [dates] if isinstance(dates, str) else dates

    def chain(self, symbol, expiration):
        d = self._get("markets/options/chains", symbol=symbol.upper(),
                      expiration=expiration, greeks="true")
        opts = (d.get("options") or {}).get("option") or []
        return [opts] if isinstance(opts, dict) else opts


TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/"
                "interest-rates/daily-treasury-rates.csv/{year}/all?"
                "type=daily_treasury_yield_curve&field_tdr_date_value={year}")


def treasury_curve(csv_text):
    """Latest row of Treasury's daily yield-curve CSV -> {"date", "points"}."""
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        return None
    latest = max(rows, key=lambda r: datetime.strptime(r["Date"], "%m/%d/%Y"))
    pts = [(k, float(v)) for k, v in latest.items() if k != "Date" and v not in (None, "")]
    return {"date": latest["Date"], "points": pts}
