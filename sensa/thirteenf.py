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


class ThirteenF:
    def __init__(self, contact, fetch):
        self.contact, self.fetch = contact.strip(), fetch

    def _get(self, url):
        if not self.contact:
            raise DataUnavailable("SEC_CONTACT not set (SEC requires a contact in the User-Agent)")
        return self.fetch(url, {"User-Agent": f"Abc-dashboard-research/1.0 {self.contact}"})

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


class Figi:
    """CUSIP -> ticker through OpenFIGI (free; 10 ids per call without a key)."""
    URL = "https://api.openfigi.com/v3/mapping"

    def __init__(self, post):
        self.post, self._map = post, {}

    def lookup(self, cusips):
        todo = [c for c in dict.fromkeys(cusips) if c not in self._map]
        for i in range(0, len(todo), 10):
            batch = todo[i:i + 10]
            res = json.loads(self.post(self.URL, [{"idType": "ID_CUSIP", "idValue": c} for c in batch]))
            for c, r in zip(batch, res):
                data = r.get("data") or []
                us = [d for d in data if d.get("exchCode") == "US" and d.get("securityType") == "Common Stock"]
                pick = (us or data or [None])[0]
                self._map[c] = pick.get("ticker") if pick else None
        return {c: self._map[c] for c in cusips if self._map.get(c)}


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
