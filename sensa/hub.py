"""Combines providers + pure calculations behind a TTL cache so free sources are
not hammered by page refreshes."""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from markov.data_providers import DataUnavailable
from sensa.thirteenf import activity, summarize
from sensa.service import SECTOR_ETFS, analyst_consensus, cp_ratio, gex, movers, sector_heatmap

TIMEFRAMES = ("15m", "30m", "1h", "4h", "1day")   # same set as markov.intraday.service
_DAILY_TTL = 6 * 3600   # daily bars: free sources allow ~25 calls/day
_FAIL_TTL = 300         # remember a failed fetch this long
_STRIKE_BAND = 0.15   # show GEX strikes within +/-15% of spot


class Hub:
    def __init__(self, cboe, news_fn, curve_fn, analyst=None, edgar=None, finra=None, candles_fn=None, thirteenf=None, figi=None, workers=6, cache_dir=None, ttl=60,
                 clock=time.monotonic, today=lambda: date.today().isoformat()):
        self.cboe, self.news_fn, self.curve_fn, self.analyst_src = cboe, news_fn, curve_fn, analyst
        self.edgar, self.finra, self.candles_fn = edgar, finra, candles_fn
        self.thirteenf, self.figi, self.workers, self.cache_dir = thirteenf, figi, workers, cache_dir
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

    # ---- 13F institutional managers (SEC filings never change once filed) ----
    def _prefetch(self, cik, filings):
        """Download several filings in parallel (SEC allows <=10 requests/s; this stays under)."""
        with ThreadPoolExecutor(max_workers=min(self.workers, max(1, len(filings)))) as pool:
            list(pool.map(lambda fl: self._raw(cik, fl), filings))

    def _filing(self, cik, fl):
        def load():
            s = summarize(self._raw(cik, fl))
            tick = self.figi.lookup([h["cusip"] for h in s["holdings"][:10]]) if self.figi else {}
            for h in s["holdings"]:
                h["ticker"] = tick.get(h["cusip"]) or h["issuer"][:12].strip()
            return s
        return self._cached(("13f", int(cik), fl["accession"]), load, ttl=10 ** 9)

    def _disk_path(self, cik, accession):
        if not (str(cik).isdigit() and re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}|[A-Za-z0-9]{1,24}", accession)):
            raise ValueError("bad cik or accession")
        return os.path.join(self.cache_dir, f"{int(cik):010d}", f"{accession}.json")

    def _raw(self, cik, fl):
        def load():
            path = self._disk_path(cik, fl["accession"]) if self.cache_dir else None
            if path is None and not str(cik).isdigit():
                raise ValueError("bad cik")
            if path and os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as fh:
                        return json.load(fh)          # filings never change once filed
                except (OSError, ValueError):
                    pass                              # corrupt entry: refetch below
            rows = self.thirteenf.holdings(cik, fl["accession"], fl["filed"])
            if path:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    tmp = path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as fh:
                        json.dump(rows, fh)
                    os.replace(tmp, path)
                except OSError:
                    pass                              # a read-only disk must not break the page
            return rows
        return self._cached(("13fraw", int(cik), fl["accession"]), load, ttl=10 ** 9)

    def _filer(self, cik):
        if self.thirteenf is None:
            raise DataUnavailable("13F not configured (set SEC_CONTACT)")
        return self._cached(("filer", int(cik)), lambda: self.thirteenf.filer(cik), ttl=3600)

    def manager(self, cik):
        f = self._filer(cik)
        if not f["filings"]:
            raise DataUnavailable("no 13F holdings reports for this filer")
        cur, prev = f["filings"][0], (f["filings"][1] if len(f["filings"]) > 1 else None)
        self._prefetch(cik, [x for x in (cur, prev) if x])
        c = self._filing(cik, cur)
        p = self._filing(cik, prev) if prev else None
        change = c["total"] - p["total"] if p else None
        pct = round(change / p["total"] * 100, 2) if p and p["total"] else None
        top = [{"ticker": h["ticker"], "name": h["issuer"], "value": h["value"], "weight": h["weight"]}
               for h in c["holdings"]]
        return {"cik": f["cik"], "name": f["name"], "location": f["location"], "latest": cur,
                "stats": {"value": c["total"], "value_change": change, "value_change_pct": pct,
                          "holdings": c["count"],
                          "holdings_change": c["count"] - p["count"] if p else None,
                          "filings": len(f["filings"]), "since": f["filings"][-1]["filed"][:4]},
                "top": top[:4], "allocation": top[:10],
                "activity": activity(self._raw(cik, cur),
                                     self._raw(cik, prev) if prev else None)}

    def manager_filings(self, cik, offset=0, limit=20):
        f = self._filer(cik)
        rows = []
        page = f["filings"][offset:offset + limit]
        self._prefetch(cik, page)
        for fl in page:
            s = self._filing(cik, fl)
            rows.append({"quarter": fl["quarter"], "holdings": s["count"], "value": s["total"],
                         "top": [h["ticker"] for h in s["holdings"][:4]], "form": fl["form"],
                         "filed": fl["filed"], "accession": fl["accession"]})
        return {"total": len(f["filings"]), "rows": rows}

    def short_volume(self, symbol):
        if self.finra is None:
            raise DataUnavailable("FINRA not configured")
        data = self._cached(("f",), lambda: self.finra.load(date.fromisoformat(self.today())),
                            ttl=3600)
        return self.finra.lookup(data, symbol)

    def yield_curve(self):
        return self._cached(("y",), self.curve_fn)
