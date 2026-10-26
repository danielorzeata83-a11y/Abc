"""Who a ticker is: name, exchange and industry from SEC, plus shares outstanding (for market cap)."""

import json
import threading

from markov.data_providers import DataUnavailable

EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


class CompanyInfo:
    def __init__(self, fetch_sec, shares_out=None):
        self.fetch, self.shares_out = fetch_sec, shares_out
        self._lock = threading.Lock()
        self._list = None
        self._cache = {}

    def get(self, ticker):
        t = (ticker or "").strip().upper()
        with self._lock:
            if t in self._cache:
                return self._cache[t]
            if self._list is None:
                raw = json.loads(self.fetch(EXCHANGE_URL))
                f = raw["fields"]
                self._list = {r[f.index("ticker")].upper(): r for r in raw["data"]}
            row = self._list.get(t)
            if row is None:
                return None
            f = ["cik", "name", "ticker", "exchange"]
            cik = int(row[0])
            industry = sic = None
            try:
                sub = json.loads(self.fetch(SUBMISSIONS_URL.format(cik=cik)))
                industry, sic = sub.get("sicDescription") or None, sub.get("sic") or None
            except (DataUnavailable, ValueError):
                pass
            sh = None
            if self.shares_out is not None:
                try:
                    sh = self.shares_out.get(t)
                except (DataUnavailable, KeyError, ValueError):
                    sh = None
            out = {"ticker": t, "name": row[1], "cik": f"{cik:010d}", "exchange": row[3], "industry": industry, "sic": sic,
                   "shares_outstanding": sh["shares"] if sh else None, "shares_as_of": sh["as_of"] if sh else None}
            self._cache[t] = out
            return out
