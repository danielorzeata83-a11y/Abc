"""SEC EDGAR insider trades (Form 4). Free, no key; SEC's fair-access policy
requires a User-Agent that names a real contact -> SEC_CONTACT env var."""

import json
import xml.etree.ElementTree as ET

from markov.data_providers import DataUnavailable

_SIDE = {"P": "buy", "S": "sell"}   # open-market purchase / sale only


def _safe_parse(text):
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise DataUnavailable("refusing XML with DTD/entities")
    try:
        return ET.fromstring(text)
    except ET.ParseError as e:
        raise DataUnavailable(f"bad XML: {e}") from e


def _f(node, path):
    return (node.findtext(path) or "").strip() if node is not None else ""


def parse_form4(xml_text):
    root = _safe_parse(xml_text)
    symbol = _f(root, "issuer/issuerTradingSymbol").upper()
    issuer = _f(root, "issuer/issuerName")
    owner = _f(root, "reportingOwner/reportingOwnerId/rptOwnerName")
    rel = root.find("reportingOwner/reportingOwnerRelationship")
    title = _f(rel, "officerTitle")
    role = title or ("Director" if _f(rel, "isDirector") in ("1", "true") else
                     "Officer" if _f(rel, "isOfficer") in ("1", "true") else
                     "10% owner" if _f(rel, "isTenPercentOwner") in ("1", "true") else "Insider")
    out = []
    for t in root.iter("nonDerivativeTransaction"):
        side = _SIDE.get(_f(t, "transactionCoding/transactionCode"))
        if not side:
            continue
        try:
            shares = float(_f(t, "transactionAmounts/transactionShares/value"))
            price = float(_f(t, "transactionAmounts/transactionPricePerShare/value") or 0)
        except ValueError:
            continue
        out.append({"symbol": symbol, "issuer": issuer, "owner": owner, "role": role,
                    "date": _f(t, "transactionDate/value"), "side": side,
                    "shares": shares, "price": price, "value": round(shares * price, 2)})
    return out


_ATOM = "{http://www.w3.org/2005/Atom}"
FEED = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4"
        "&company=&dateb=&owner=include&start=0&count={count}&output=atom")


class Edgar:
    def __init__(self, contact, fetch):
        self.contact, self.fetch = contact.strip(), fetch

    def _get(self, url):
        ua = f"Abc-dashboard-research/1.0 {self.contact}"   # SEC fair-access format
        return self.fetch(url, {"User-Agent": ua})

    def recent(self, symbol=None, limit=10, scan=25):
        if not self.contact:
            raise DataUnavailable("SEC_CONTACT not set (SEC requires a contact in the User-Agent)")
        feed = _safe_parse(self._get(FEED.format(count=scan)))
        trades = []
        for entry in feed.iter(_ATOM + "entry"):
            link = entry.find(_ATOM + "link")
            href = link.get("href", "") if link is not None else ""
            if not href.endswith("-index.htm"):
                continue
            base = href.rsplit("/", 1)[0]
            try:
                items = json.loads(self._get(base + "/index.json"))["directory"]["item"]
                name = next(i["name"] for i in items
                            if i["name"].endswith(".xml") and "/" not in i["name"])
                trades += parse_form4(self._get(f"{base}/{name}"))
            except (DataUnavailable, StopIteration, KeyError, ValueError):
                continue    # one bad filing must not hide the rest
            if symbol and trades and len([t for t in trades if t["symbol"] == symbol.upper()]) >= limit:
                break
            if not symbol and len(trades) >= limit:
                break
        if symbol:
            trades = [t for t in trades if t["symbol"] == symbol.upper()]
        return trades[:limit]
