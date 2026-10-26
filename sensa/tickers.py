"""Ticker -> CUSIP. 13F filings carry CUSIPs only, so a ticker is matched by issuer name and then confirmed:
OpenFIGI names the ticker, the filings' issuer names narrow the candidates, and OpenFIGI's reverse lookup of
each candidate's CUSIP must return the same ticker before it is accepted."""

import json
import os
import re

from sensa.holders import cusips_by_issuer, has_holders

_TICKER = re.compile(r"[A-Z0-9]{1,6}([.\-][A-Z0-9]{1,2})?")
_MAX_PREFIXES = 4


def _name_prefixes(name):
    words = re.sub(r"/[A-Z]{1,3}$", "", re.sub(r"[^A-Z0-9 /&.\-]", " ", name.upper()).strip()).split()
    words = [w.strip(".,") for w in words if w.strip(".,")]
    return [" ".join(words[:n]) for n in range(len(words), 0, -1)][:_MAX_PREFIXES]


class TickerResolver:
    def __init__(self, db_path, post, figi, cache_path=None):
        self.db_path, self.post, self.figi, self.cache_path = db_path, post, figi, cache_path
        self._found = {}
        if cache_path:
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    self._found = {k: v for k, v in json.load(fh).items() if isinstance(v, str)}
            except (OSError, ValueError, AttributeError):
                self._found = {}

    def cusip(self, ticker):
        t = (ticker or "").strip().upper()
        if not _TICKER.fullmatch(t):
            return None
        if t in self._found:
            return self._found[t]
        found = self._from_cache(t) or self._from_name(t)
        if found:
            self._found[t] = found
            self._save()
        return found

    def _from_cache(self, t):
        known = self.figi.cusips_for(t)
        for c in known:                                  # only a CUSIP that some filer actually holds
            if has_holders(self.db_path, c):
                return c
        return None

    def _from_name(self, t):
        res = json.loads(self.post(self.figi.URL, [{"idType": "TICKER", "idValue": t, "exchCode": "US"}]))
        data = (res[0].get("data") if res else None) or []
        stocks = [d for d in data if d.get("securityType") == "Common Stock"] or data
        name = next((d.get("name") for d in stocks if d.get("name")), None)
        if not name:
            return None
        for prefix in _name_prefixes(name):
            cands = [c for c, _ in cusips_by_issuer(self.db_path, prefix, limit=10)]
            if not cands:
                continue
            info = self.figi.info(cands)
            for c in cands:                              # already ranked by size
                if (info.get(c) or {}).get("ticker") == t:
                    return c
        return None

    def _save(self):
        if not self.cache_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._found, fh)
            os.replace(tmp, self.cache_path)
        except OSError:
            pass

