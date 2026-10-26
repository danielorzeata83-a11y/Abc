"""Combines providers + pure calculations behind a TTL cache so the free tiers
(Finnhub: 60 calls/min) are not exhausted by page refreshes."""

import time

from markov.data_providers import DataUnavailable
from sensa.service import analyst_consensus, cp_ratio, movers


class Hub:
    def __init__(self, finnhub, tradier, treasury_text, ttl=60, clock=time.monotonic):
        self.fh, self.tr, self._treasury_text = finnhub, tradier, treasury_text
        self.ttl, self.clock, self._cache = ttl, clock, {}

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
                quotes[s] = self._cached(("q", s), lambda s=s: self.fh.quote(s))
            except DataUnavailable:
                continue
        return movers(quotes, n)

    def analyst(self, symbol):
        s = symbol.upper()
        return analyst_consensus(self._cached(("a", s), lambda: self.fh.recommendations(s)))

    def news(self, symbol=None, limit=12):
        return self._cached(("n", symbol), lambda: self.fh.news(symbol))[:limit]

    def options(self, symbol):
        s = symbol.upper()

        def load():
            exps = self.tr.expirations(s)
            if not exps:
                return None
            chain = self.tr.chain(s, exps[0])
            return {"symbol": s, "expiration": exps[0], "cp": cp_ratio(chain), "chain": chain}
        return self._cached(("o", s), load)

    def yield_curve(self):
        from sensa.providers import treasury_curve
        return self._cached(("y",), lambda: treasury_curve(self._treasury_text()))
