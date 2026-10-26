"""Combines providers + pure calculations behind a TTL cache so free sources are
not hammered by page refreshes."""

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from markov.data_providers import DataUnavailable
from sensa.thirteenf import activity, changes, summarize
from sensa.service import SECTOR_ETFS, analyst_consensus, cp_ratio, gex, movers, sector_heatmap

TIMEFRAMES = ("15m", "30m", "1h", "4h", "1day")   # same set as markov.intraday.service
_DAILY_TTL = 6 * 3600   # daily bars: free sources allow ~25 calls/day
_FAIL_TTL = 300         # remember a failed fetch this long
_STRIKE_BAND = 0.15   # show GEX strikes within +/-15% of spot


class Hub:
    def __init__(self, cboe, news_fn, curve_fn, analyst=None, edgar=None, finra=None, candles_fn=None, thirteenf=None, figi=None, workers=6, cache_dir=None, accession_lookup=None, ttl=60,
                 clock=time.monotonic, today=lambda: date.today().isoformat()):
        self.cboe, self.news_fn, self.curve_fn, self.analyst_src = cboe, news_fn, curve_fn, analyst
        self.edgar, self.finra, self.candles_fn = edgar, finra, candles_fn
        self.thirteenf, self.figi, self.workers, self.cache_dir = thirteenf, figi, workers, cache_dir
        self.accession_lookup, self._reg_lock = accession_lookup, threading.Lock()
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
        f = self._cached(("filer", int(cik)), lambda: self.thirteenf.filer(cik), ttl=600)
        self._register(cik, [x["accession"] for x in f["filings"]])
        return f

    # ---- accession registry: /institutional-investor/<accession> needs to know whose filing it is ----
    @staticmethod
    def _acc_key(accession):
        return accession.replace("-", "").lower()

    def _registry_path(self):
        return os.path.join(self.cache_dir, "accessions.json") if self.cache_dir else None

    def _registry(self):
        reg = self._cache.get(("registry",))
        if reg is None:
            reg = {}
            path = self._registry_path()
            if path:
                try:
                    with open(path, encoding="utf-8") as fh:
                        reg = json.load(fh)
                except (OSError, ValueError):
                    reg = {}
            self._cache[("registry",)] = (self.clock() + 10 ** 9, reg)   # kept for the process lifetime
            return reg
        return reg[1] if isinstance(reg, tuple) else reg

    def _register(self, cik, accessions):
        with self._reg_lock:
            reg, changed = self._registry(), False
            for a in accessions:
                k = self._acc_key(a)
                if reg.get(k) != [f"{int(cik):010d}", a]:
                    reg[k], changed = [f"{int(cik):010d}", a], True
            path = self._registry_path()
            if changed and path:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    tmp = path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as fh:
                        json.dump(reg, fh)
                    os.replace(tmp, path)
                except OSError:
                    pass

    def cik_for_accession(self, accession):
        """(cik, dashed accession) for a filing we have seen before, else None."""
        hit = self._registry().get(self._acc_key(accession))
        if hit:
            return hit[0], hit[1]
        if self.accession_lookup:
            return self.accession_lookup(self._acc_key(accession))
        return None

    def _disk_json(self, cik, name, load):
        """Immutable per-filing JSON on disk (cover pages, holdings): read it, else load() and save it."""
        if not self.cache_dir:
            return load()
        path = os.path.join(self.cache_dir, f"{int(cik):010d}", name)
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass
        val = load()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(val, fh)
            os.replace(tmp, path)
        except OSError:
            pass
        return val

    def latest_filings(self, limit=50):
        """Newest 13F reports, one per manager, with period / positions / value from each cover page."""
        if self.thirteenf is None:
            raise DataUnavailable("13F not configured (set SEC_CONTACT)")
        rows = self._cached(("latest", limit), lambda: self.thirteenf.latest(limit), ttl=300)
        self._register_many(rows)

        def one(r):
            try:
                c = self._disk_json(r["cik"], f"{r['accession']}.cover.json",
                                    lambda: self.thirteenf.cover(r["cik"], r["accession"], r["filed"]))
                return {**r, "quarter": c["quarter"], "period": c["period"], "entries": c["entries"], "value": c["value"]}
            except DataUnavailable:
                return {**r, "quarter": None, "period": None, "entries": None, "value": None}
        with ThreadPoolExecutor(max_workers=min(self.workers, max(1, len(rows)))) as pool:
            return list(pool.map(one, rows))

    def _register_many(self, rows):
        for r in rows:
            self._register(r["cik"], [r["accession"]])

    def filing(self, accession):
        """One report: header, stats vs the previous quarter, holdings with the change in each position."""
        hit = self.cik_for_accession(accession)
        if not hit:
            raise DataUnavailable("filing not found: open it from the manager page or the latest filings list")
        cik, dashed = hit
        f = self._filer(cik)
        cur = next((x for x in f["filings"] if x["accession"] == dashed), None)
        if cur is None:
            raise DataUnavailable("filing not found for this manager")
        older = [x for x in f["filings"] if x["period"] < cur["period"]]
        prev = max(older, key=lambda x: (x["period"], x["filed"])) if older else None
        self._prefetch(cik, [x for x in (cur, prev) if x])
        rows, prev_rows = self._raw(cik, cur), self._raw(cik, prev) if prev else None
        s = summarize(rows)
        ps = summarize(prev_rows) if prev_rows is not None else None
        tick = self.figi.lookup([h["cusip"] for h in s["holdings"][:100]]) if self.figi else {}
        pmap = {r["cusip"]: r for r in (prev_rows or [])}
        out = []
        for h in s["holdings"][:100]:
            p = pmap.get(h["cusip"])
            ch = None
            if prev_rows is not None:
                if p is None:
                    ch = {"type": "new", "shares_delta": h["shares"], "pct": None}
                elif h["shares"] != p["shares"]:
                    ch = {"type": "increased" if h["shares"] > p["shares"] else "reduced",
                          "shares_delta": h["shares"] - p["shares"],
                          "pct": round((h["shares"] - p["shares"]) / p["shares"] * 100, 2) if p["shares"] else None}
            out.append({"ticker": tick.get(h["cusip"]) or h["issuer"][:12].strip(), "issuer": h["issuer"],
                        "cusip": h["cusip"], "shares": h["shares"], "value": h["value"], "weight": h["weight"],
                        "change": ch})
        now = {r["cusip"] for r in rows}
        exited = [{"issuer": p["issuer"], "cusip": p["cusip"], "shares": p["shares"], "value": p["value"]}
                  for p in sorted(prev_rows or [], key=lambda r: -r["value"]) if p["cusip"] not in now][:50]
        return {"cik": f["cik"], "name": f["name"], "location": f["location"], "accession": dashed,
                "quarter": cur["quarter"], "period": cur["period"], "form": cur["form"], "filed": cur["filed"],
                "prev_quarter": prev["quarter"] if prev else None,
                "stats": {"value": s["total"], "positions": s["count"],
                          "value_change": s["total"] - ps["total"] if ps else None,
                          "value_change_pct": round((s["total"] - ps["total"]) / ps["total"] * 100, 2) if ps and ps["total"] else None,
                          "positions_change": s["count"] - ps["count"] if ps else None},
                "holdings": out, "truncated": s["count"] > 100, "exited": exited}

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
