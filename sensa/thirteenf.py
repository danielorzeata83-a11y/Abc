"""13F institutional-manager data from SEC EDGAR (public filings, free).

Pure helpers first; the EDGAR client and OpenFIGI ticker lookup follow below."""


def quarter_label(report_period):
    """'2026-06-30' -> 'Q2 2026' (calendar quarter of the report period)."""
    year, month = report_period[:4], int(report_period[5:7])
    return f"Q{(month - 1) // 3 + 1} {year}"


def aggregate(rows):
    """Merge info-table lines that share a CUSIP (13F repeats an issuer per manager/discretion)."""
    merged = {}
    for r in rows:
        m = merged.get(r["cusip"])
        if m is None:
            merged[r["cusip"]] = dict(r)
        else:
            m["value"] += r["value"]
            m["shares"] += r["shares"]
    return list(merged.values())


def summarize(rows):
    total = sum(r["value"] for r in rows)
    holdings = sorted(({**r, "weight": round(r["value"] / total * 100, 2)} for r in rows),
                      key=lambda r: r["value"], reverse=True) if total else []
    return {"total": float(total), "count": len(rows), "holdings": holdings}


def activity(current, previous):
    """Position changes vs the prior quarter, judged by share count."""
    prev = {r["cusip"]: r["shares"] for r in (previous or [])}
    cur = {r["cusip"]: r["shares"] for r in current}
    out = {"new": 0, "increased": 0, "reduced": 0, "exited": 0}
    for cusip, sh in cur.items():
        if cusip not in prev:
            out["new"] += 1
        elif sh > prev[cusip]:
            out["increased"] += 1
        elif sh < prev[cusip]:
            out["reduced"] += 1
    out["exited"] = sum(1 for c in prev if c not in cur)
    return out


import json
import os
import re
import xml.etree.ElementTree as ET

from markov.data_providers import DataUnavailable

_DOLLARS_SINCE = "2023-01-03"   # SEC switched 13F value reporting from $thousands to $
_SUB = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARCH = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}"


def _safe_xml(text):
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise DataUnavailable("refusing XML with DTD/entities")
    try:
        return ET.fromstring(text)
    except ET.ParseError as e:
        raise DataUnavailable(f"bad XML: {e}") from e


_ATOM13 = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=13F-HR&company=&dateb=&owner=include"
          "&start=0&count={count}&output=atom")
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_TITLE = re.compile(r"^(13F-HR(?:/A)?) - (.+?) \((\d{1,10})\) \((?:Filer|Subject)\)$")
_ACC_LINK = re.compile(r"/data/\d+/(\d{10})(\d{2})(\d{6})/")
_FILED = re.compile(r"Filed:.{0,30}?(\d{4}-\d{2}-\d{2})")


class ThirteenF:
    def __init__(self, contact, fetch):
        self.contact, self.fetch = contact.strip(), fetch

    def _get(self, url):
        if not self.contact:
            raise DataUnavailable("SEC_CONTACT not set (SEC requires a contact in the User-Agent)")
        return self.fetch(url, {"User-Agent": f"Abc-dashboard-research/1.0 {self.contact}"})

    def latest(self, limit=50, scan=100):
        """Newest 13F reports on EDGAR, one row per manager (their newest), newest first."""
        feed = _safe_xml(self._get(_ATOM13.format(count=scan)))
        out, seen = [], set()
        for e in feed.iter(_ATOM_NS + "entry"):
            t = _TITLE.match((e.findtext(_ATOM_NS + "title") or "").strip())
            link = e.find(_ATOM_NS + "link")
            a = _ACC_LINK.search(link.get("href", "") if link is not None else "")
            if not t or not a:
                continue
            cik = f"{int(t.group(3)):010d}"
            if cik in seen:
                continue
            seen.add(cik)
            filed = _FILED.search(__import__("html").unescape(e.findtext(_ATOM_NS + "summary") or ""))
            out.append({"cik": cik, "name": t.group(2), "form": t.group(1), "filed": filed.group(1) if filed else "",
                        "accession": "-".join(a.groups())})
            if len(out) >= limit:
                break
        return out

    def cover(self, cik, accession, filed=None):
        """Period, number of positions and total value of one report (from its primary_doc.xml)."""
        base = _ARCH.format(cik=int(cik), acc=accession.replace("-", ""))
        root = _safe_xml(self._get(base + "/primary_doc.xml"))
        raw = (root.findtext(".//{*}reportCalendarOrQuarter") or root.findtext(".//{*}periodOfReport") or "").strip()
        try:
            mm, dd, yy = raw.split("-")
            period = f"{int(yy):04d}-{int(mm):02d}-{int(dd):02d}"
            entries = int(root.findtext(".//{*}tableEntryTotal") or 0)
            value = float(root.findtext(".//{*}tableValueTotal") or 0)
        except ValueError:
            raise DataUnavailable(f"unreadable cover page for {accession}") from None
        if filed and filed < _DOLLARS_SINCE:
            value *= 1000.0
        return {"period": period, "quarter": quarter_label(period), "entries": entries, "value": value,
                "name": (root.findtext(".//{*}filingManager/{*}name") or "").strip()}

    def filer(self, cik):
        cik_i = int(cik)
        d = json.loads(self._get(_SUB.format(cik=cik_i)))
        b = (d.get("addresses") or {}).get("business") or {}
        loc = ", ".join(x for x in (str(b.get("city") or "").title(), b.get("stateOrCountry")) if x)
        r = d["filings"]["recent"]
        filings = [{"quarter": quarter_label(r["reportDate"][i]), "period": r["reportDate"][i],
                    "filed": r["filingDate"][i], "accession": r["accessionNumber"][i],
                    "form": r["form"][i]}
                   for i in range(len(r["form"])) if r["form"][i].startswith("13F-HR")]
        filings.sort(key=lambda x: x["period"], reverse=True)
        return {"cik": f"{cik_i:010d}", "name": d["name"], "location": loc, "filings": filings}

    def holdings(self, cik, accession, filed=None):
        # Before 2023 Form 13F values were in thousands of dollars; since then whole dollars.
        scale = 1000.0 if filed and filed < _DOLLARS_SINCE else 1.0
        base = _ARCH.format(cik=int(cik), acc=accession.replace("-", ""))
        items = json.loads(self._get(base + "/index.json"))["directory"]["item"]
        names = [i["name"] for i in items
                 if i["name"].lower().endswith(".xml") and not i["name"].lower().startswith("primary_doc")]
        for name in names:
            root = _safe_xml(self._get(f"{base}/{name}"))
            tables = root.findall(".//{*}infoTable")
            if not tables:
                continue
            rows = []
            for it in tables:
                g = lambda p: (it.findtext("{*}" + p) or "").strip()
                try:
                    rows.append({"issuer": g("nameOfIssuer"), "cusip": g("cusip"),
                                 "value": float(g("value")) * scale,
                                 "shares": float(it.findtext("{*}shrsOrPrnAmt/{*}sshPrnamt") or 0)})
                except ValueError:
                    continue
            return aggregate(rows)
        raise DataUnavailable(f"no information table in filing {accession}")


_NORMAL = re.compile(r"[A-Z]{1,6}([./-][A-Z])?")


class Figi:
    """CUSIP -> ticker/kind through OpenFIGI (free: 10 ids per call, ~25 calls/min without a key)."""
    URL = "https://api.openfigi.com/v3/mapping"
    _KIND = {"Common Stock": "stock", "ETP": "etf", "ADR": "adr", "Depositary Receipt": "adr"}

    def __init__(self, post, sleep=None, min_interval=0.0, cache_path=None, clock=None):
        import threading
        import time
        self.post, self.min_interval, self.cache_path = post, min_interval, cache_path
        self._sleep, self._clock = sleep or time.sleep, clock or time.monotonic
        self._lock, self._last = threading.Lock(), None
        self._map = {}
        if cache_path:
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    self._map = {k: v for k, v in json.load(fh).items()}
            except (OSError, ValueError, AttributeError):
                self._map = {}

    def _save(self):
        if not self.cache_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._map, fh)
            os.replace(tmp, self.cache_path)
        except OSError:
            pass                                        # a read-only disk must not break lookups

    def cusips_for(self, ticker):
        """CUSIPs already looked up whose ticker is `ticker` (no network)."""
        with self._lock:
            return [c for c, v in self._map.items() if v and v.get("ticker") == ticker]

    def info(self, cusips):
        with self._lock:                                  # one request at a time, spaced for the free rate limit
            return self._info(cusips)

    def request(self, payload):
        """One OpenFIGI mapping call, spaced and serialised with every other call (free rate limit)."""
        with self._lock:
            return self._post_spaced(payload)

    def _post_spaced(self, payload):
        if self.min_interval and self._last is not None:
            wait = self.min_interval - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        try:
            return json.loads(self.post(self.URL, payload))
        finally:
            self._last = self._clock()

    def _info(self, cusips):
        todo = [c for c in dict.fromkeys(cusips) if c not in self._map]
        for i in range(0, len(todo), 10):
            batch = todo[i:i + 10]
            res = self._post_spaced([{"idType": "ID_CUSIP", "idValue": c} for c in batch])
            for c, r in zip(batch, res):
                data = r.get("data") or []
                stocks = [d for d in data if d.get("securityType") == "Common Stock"] or data

                def rank(d):                      # US composite first, then a normal-looking ticker, then the shortest
                    t = d.get("ticker") or ""
                    return (d.get("exchCode") != "US", not _NORMAL.fullmatch(t), len(t) or 99)
                pick = min(stocks, key=rank) if stocks else None
                self._map[c] = ({"ticker": pick.get("ticker"),
                                 "kind": self._KIND.get(pick.get("securityType"), "other")}
                                if pick and pick.get("ticker") else None)
            self._save()
        return {c: self._map[c] for c in cusips if self._map.get(c)}

    def lookup(self, cusips):
        return {c: v["ticker"] for c, v in self.info(cusips).items()}


def changes(current, previous):
    """Position-level diff between two quarters (by CUSIP, judged on share count).
    No previous filing -> no diff (a first filing is a baseline, not a signal)."""
    if previous is None:
        return []
    prev = {r["cusip"]: r for r in previous}
    cur = {r["cusip"]: r for r in current}
    out = []

    def row(kind, c, p):
        return {"type": kind, "cusip": (c or p)["cusip"], "issuer": (c or p)["issuer"],
                "shares_now": c["shares"] if c else 0.0, "shares_prev": p["shares"] if p else 0.0,
                "value_now": c["value"] if c else 0.0, "value_prev": p["value"] if p else 0.0}
    for cusip, c in cur.items():
        p = prev.get(cusip)
        if p is None:
            out.append(row("new", c, None))
        elif c["shares"] > p["shares"]:
            out.append(row("increased", c, p))
        elif c["shares"] < p["shares"]:
            out.append(row("reduced", c, p))
    out += [row("exited", None, p) for cusip, p in prev.items() if cusip not in cur]
    return sorted(out, key=lambda r: max(r["value_now"], r["value_prev"]), reverse=True)
