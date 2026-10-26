"""Combines providers + pure calculations behind a TTL cache so free sources are
not hammered by page refreshes."""

import time
from datetime import date

from markov.data_providers import DataUnavailable
from sensa.service import SECTOR_ETFS, analyst_consensus, cp_ratio, gex, movers, sector_heatmap

TIMEFRAMES = ("15m", "30m", "1h", "4h", "1day")   # same set as markov.intraday.service
_DAILY_TTL = 6 * 3600   # daily bars: free sources allow ~25 calls/day
_FAIL_TTL = 300         # remember a failed fetch this long
_STRIKE_BAND = 0.15   # show GEX strikes within +/-15% of spot


class Hub:
    def __init__(self, cboe, news_fn, curve_fn, analyst=None, edgar=None, finra=None, candles_fn=None, ttl=60,
                 clock=time.monotonic, today=lambda: date.today().isoformat()):
        self.cboe, self.news_fn, self.curve_fn, self.analyst_src = cboe, news_fn, curve_fn, analyst
        self.edgar, self.finra, self.candles_fn = edgar, finra, candles_fn
        self.ttl, self.clock, self.today, self._cache = ttl, clock, today, {}

    def _cached(self, key, load, ttl=None):
        hit = self._cache.get(key)
        if hit and self.clock() - hit[0] < (self.ttl if ttl is None else ttl):
            return hit[1]
        val = load()
        self._cache[key] = (self.clock(), val)
        return val

    def _quotes(self, symbols):
        quotes = {}
        for s in symbols:
            try:
                quotes[s] = self._cached(("q", s), lambda s=s: self.cboe.quote(s))
            except DataUnavailable:
                continue
        return quotes

    def movers(self, symbols, n=5):
        return movers(self._quotes(symbols), n)

    def sectors(self):
        return sector_heatmap(self._quotes(SECTOR_ETFS))

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

    def insiders(self, symbol=None, limit=10):
        if self.edgar is None:
            raise DataUnavailable("EDGAR not configured (set SEC_CONTACT)")
        return self._cached(("i", symbol, limit), lambda: self.edgar.recent(symbol, limit), ttl=300)

    def candles(self, symbol, tf):
        if self.candles_fn is None:
            raise DataUnavailable("candles not configured")
        if tf not in TIMEFRAMES:
            raise ValueError(f"bad timeframe {tf!r}")
        s = symbol.upper()
        key = ("c", s, tf)
        failed = self._cache.get(key + ("err",))
        if failed and self.clock() - failed[0] < _FAIL_TTL:    # don't re-spend a free quota
            raise DataUnavailable(failed[1])
        try:
            return self._cached(key, lambda: self.candles_fn(s, tf),
                                ttl=_DAILY_TTL if tf == "1day" else None)
        except DataUnavailable as e:
            self._cache[key + ("err",)] = (self.clock(), str(e))
            raise

    def short_volume(self, symbol):
        if self.finra is None:
            raise DataUnavailable("FINRA not configured")
        data = self._cached(("f",), lambda: self.finra.load(date.fromisoformat(self.today())),
                            ttl=3600)
        return self.finra.lookup(data, symbol)

    def yield_curve(self):
        return self._cached(("y",), self.curve_fn)
