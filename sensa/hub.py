"""Combines providers + pure calculations behind a TTL cache so free sources are
not hammered by page refreshes."""

import time
from datetime import date

from markov.data_providers import DataUnavailable
from sensa.service import analyst_consensus, cp_ratio, gex, movers

_STRIKE_BAND = 0.15   # show GEX strikes within +/-15% of spot


class Hub:
    def __init__(self, cboe, news_fn, curve_fn, analyst=None, ttl=60,
                 clock=time.monotonic, today=lambda: date.today().isoformat()):
        self.cboe, self.news_fn, self.curve_fn, self.analyst_src = cboe, news_fn, curve_fn, analyst
        self.ttl, self.clock, self.today, self._cache = ttl, clock, today, {}

    def _cached(self, key, load):
        hit = self._cache.get(key)
        if hit and self.clock() - hit[0] < self.ttl:
            return hit[1]
        val = load()
        self._cache[key] = (self.clock(), val)
        return val

    def movers(self, symbols, n=5):
        quotes = {}
        for s in symbols:
            try:
                quotes[s] = self._cached(("q", s), lambda s=s: self.cboe.quote(s))
            except DataUnavailable:
                continue
        return movers(quotes, n)

    def analyst(self, symbol):
        if self.analyst_src is None:
            return None
        s = symbol.upper()
        return analyst_consensus(self._cached(("a", s), lambda: self.analyst_src.recommendations(s)))

    def news(self, symbol=None, limit=12):
        return self._cached(("n", symbol), lambda: self.news_fn(symbol))[:limit]

    def options(self, symbol):
        s = symbol.upper()

        def load():
            spot, chain = self.cboe.chain(s)
            if not chain:
                return None
            exp = min(o["expiration"] for o in chain)
            near = [o for o in chain if o["expiration"] == exp]
            g = gex(near, spot)
            g["by_strike"] = [r for r in g["by_strike"]
                              if abs(r["strike"] - spot) <= spot * _STRIKE_BAND]
            return {"symbol": s, "spot": spot, "expiration": exp,
                    "zero_dte": exp == self.today(), "cp": cp_ratio(near), "gex": g,
                    "chain": near}
        return self._cached(("o", s), load)

    def yield_curve(self):
        return self._cached(("y",), self.curve_fn)
