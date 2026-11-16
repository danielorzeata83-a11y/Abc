"""Shares outstanding per ticker, from SEC (company_tickers.json + XBRL dei:EntityCommonStockSharesOutstanding).
Companies with several share classes report one count per class; the share count is then ambiguous and left out."""

import json
import os
import threading
import time

from markov.data_providers import DataUnavailable

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityCommonStockSharesOutstanding.json"
_TTL = 30 * 86400


class SharesOutstanding:
    def __init__(self, fetch, cache_path=None, clock=time.time):
        self.fetch, self.cache_path, self._clock = fetch, cache_path, clock
        self._lock = threading.Lock()
        self._ciks = None
        self._cache = {}
        if cache_path:
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    self._cache = {k: v for k, v in json.load(fh).items() if isinstance(v, dict)}
            except (OSError, ValueError, AttributeError):
                self._cache = {}

    def get(self, ticker):
        """{'shares', 'as_of'} or None."""
        t = (ticker or "").strip().upper()
        with self._lock:
            hit = self._cache.get(t)
            if hit and self._clock() - hit.get("at", 0) < _TTL:
                return {"shares": hit["shares"], "as_of": hit["as_of"]}
            found = self._lookup(t)
            if found:
                self._cache[t] = {**found, "at": self._clock()}
                self._save()
            return found

    def _lookup(self, t):
        if self._ciks is None:
            raw = json.loads(self.fetch(TICKERS_URL))
            self._ciks = {v["ticker"].upper(): int(v["cik_str"]) for v in raw.values()}
        cik = self._ciks.get(t)
        if cik is None:
            return None
        try:
            facts = json.loads(self.fetch(CONCEPT_URL.format(cik=cik)))["units"]["shares"]
        except (DataUnavailable, KeyError, ValueError):
            return None
        if not facts:
            return None
        latest = max(f["end"] for f in facts)
        vals = {f["val"] for f in facts if f["end"] == latest}
        return {"shares": vals.pop(), "as_of": latest} if len(vals) == 1 else None

    def _save(self):
        if not self.cache_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._cache, fh)
            os.replace(tmp, self.cache_path)
        except OSError:
            pass
