"""Institutional investors holding one stock: rows, summary, sorting and paging (same shape as the original site's API)."""

import re

from sensa.holders import holders_for_cusip, live_meta, meta, sold_out_count
from sensa.thirteenf import quarter_label

CONTRACT_MULTIPLIER = 100
MAX_LIMIT = 200

# Editable: a filer whose name contains one of these is flagged as a prime broker / bank.
PRIME_BROKER_PATTERNS = (
    "GOLDMAN SACHS", "MORGAN STANLEY", "JPMORGAN", "J P MORGAN", "BANK OF AMERICA", "CITIGROUP", "CREDIT SUISSE",
    "UBS GROUP", "UBS AG", "BARCLAYS", "DEUTSCHE BANK", "BNP PARIBAS", "WELLS FARGO", "NOMURA", "SOCIETE GENERALE",
    "HSBC", "BMO", "ROYAL BANK OF CANADA", "TORONTO DOMINION", "MIZUHO", "JEFFERIES", "CANTOR FITZGERALD")

SORT_KEYS = ("value", "shares", "name", "stockValue", "optionsValue", "callValue", "putValue", "callShares", "putShares",
             "optionPositions", "ownershipPct", "prevShares", "prevStockValue", "shareChange", "shareChangePct",
             "aum", "filed")


def is_prime_broker(name):
    n = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper())
    n = " ".join(n.split())
    return any(p in n for p in PRIME_BROKER_PATTERNS)


def _pct(part, whole):
    return round(part / whole * 100, 2) if whole else None


def _row(h, shares_out, top_ciks, labels):
    call, put = h["call_value"], h["put_value"]
    options = call - put                                  # net call - put, as the original reports it
    prev = h["prev_shares"]
    change = h["shares"] - (prev or 0)
    if not h["stock_positions"]:
        kind = "OPTIONS"
    elif prev is None:
        kind = "NEW"
    else:
        kind = "INCREASED" if change > 0 else "DECREASED" if change < 0 else "UNCHANGED"
    if prev is not None and prev > 0:
        change_pct = round(change / prev * 100, 2)
    else:
        change_pct = None
    return {
        "cik": h["cik"], "name": h["name"], "accession": h["accession"], "filed": h["filed"], "form": h["form"], "aum": h["aum"],
        "value": h["stock_value"] + options, "shares": h["shares"],
        "isTopFund": h["cik"] in top_ciks, "isPrimeBroker": is_prime_broker(h["name"]),
        "stockValue": h["stock_value"], "optionsValue": options, "callValue": call, "putValue": put,
        "stockShares": h["shares"], "callShares": h["call_shares"], "putShares": h["put_shares"],
        "callContracts": h["call_shares"] / CONTRACT_MULTIPLIER, "putContracts": h["put_shares"] / CONTRACT_MULTIPLIER,
        "optionPositions": h["option_positions"],
        "ownershipPct": _pct(h["shares"], shares_out["shares"]) if shares_out else None,
        "prevShares": prev or 0, "prevStockValue": h["prev_stock_value"] or 0,
        "shareChange": change, "shareChangePct": change_pct, "changeType": kind,
        "isCurrent": h["is_current"],
        "history": [{"label": lab, "shares": (sh or 0) if rep else None, "stockValue": (val or 0) if rep else None, "reported": rep}
                    for lab, (sh, val, rep) in zip(labels, h["hist"])],
    }


def _sort_key(key):
    def k(r):
        v = r[key]
        return v.lower() if isinstance(v, str) else v
    return k


def investors_page(db_path, cusip, ticker, shares_out=None, top_ciks=frozenset(), page=1, limit=20,
                   sort_by="value", sort_order="desc", live_db=None):
    if sort_by not in SORT_KEYS:
        raise ValueError(f"sortBy must be one of {', '.join(SORT_KEYS)}")
    if sort_order not in ("asc", "desc"):
        raise ValueError("sortOrder must be asc or desc")
    if page < 1 or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"page must be >= 1 and limit between 1 and {MAX_LIMIT}")
    m = meta(db_path)
    labels = [quarter_label(m["prev_period"]), quarter_label(m["period"])]
    live = live_meta(live_db, m["period"])
    if live:
        labels.append(quarter_label(live["period"]))
    rows = [_row(h, shares_out, top_ciks, labels) for h in holders_for_cusip(db_path, cusip, live_db if live else None)]
    present = sorted((r for r in rows if r[sort_by] is not None), key=_sort_key(sort_by), reverse=sort_order == "desc")
    ordered = present + [r for r in rows if r[sort_by] is None]          # unknown values last in both directions
    stock_value, stock_shares = sum(r["stockValue"] for r in rows), sum(r["shares"] for r in rows)
    call, put = sum(r["callValue"] for r in rows), sum(r["putValue"] for r in rows)
    total = stock_value + call - put
    summary = {
        "ticker": ticker, "cusip": cusip, "filerCount": len(rows),
        "filersWithOptions": sum(1 for r in rows if r["optionPositions"]),
        "topFundCount": sum(1 for r in rows if r["isTopFund"]), "primeBrokerCount": sum(1 for r in rows if r["isPrimeBroker"]),
        "callFilerCount": sum(1 for r in rows if r["callShares"]), "putFilerCount": sum(1 for r in rows if r["putShares"]),
        "totalValue": total, "stockValue": stock_value, "optionsValue": call - put, "callValue": call, "putValue": put,
        "stockShares": stock_shares, "contractMultiplier": CONTRACT_MULTIPLIER,
        "optionsPct": _pct(abs(call - put), total) if total else 0,
        "newCount": sum(1 for r in rows if r["changeType"] == "NEW"),
        "increasedCount": sum(1 for r in rows if r["changeType"] == "INCREASED"),
        "decreasedCount": sum(1 for r in rows if r["changeType"] == "DECREASED"),
        "soldOutCount": sold_out_count(db_path, cusip, live_db if live else None),
        "sharesOutstanding": shares_out["shares"] if shares_out else None,
        "sharesOutstandingAsOf": shares_out["as_of"] if shares_out else None,
        "heldPct": _pct(stock_shares, shares_out["shares"]) if shares_out else None}
    start = (page - 1) * limit
    now = sum(1 for r in rows if r["isCurrent"])
    coverage = {"quarter": labels[-1], "period": live["period"] if live else m["period"], "filers": len(rows),
                "currentFilers": now if live else len(rows), "carriedFilers": len(rows) - now if live else 0,
                "carriedFrom": labels[1] if live else None,
                "currentTotalValue": sum(r["stockValue"] for r in rows if r["isCurrent"]) if live else None}
    return {"summary": summary, "coverage": coverage,
            "quarters": [{"label": x} for x in labels], "data": ordered[start:start + limit],
            "pagination": {"page": page, "limit": limit, "total": len(rows), "totalPages": -(-len(rows) // limit)},
            "sort": {"sortBy": sort_by, "sortOrder": sort_order}}


class UnknownTicker(Exception):
    """The ticker could not be matched to a security that 13F filers hold."""


class InvestorService:
    def __init__(self, data_dir, figi, fetch_sec, live_db=None):
        import os
        from sensa.shares_out import SharesOutstanding
        from sensa.tickers import TickerResolver
        self.data_dir = data_dir
        self.db = os.path.join(data_dir, "holders.db")
        self.live_db = live_db or os.path.join(data_dir, "live13f.db")
        self.resolver = TickerResolver(self.db, figi, cache_path=os.path.join(data_dir, "tickers.json"))
        self.shares_out = SharesOutstanding(fetch_sec, os.path.join(data_dir, "shares_out.json"))

    def _top_ciks(self):
        from markov.data_providers import DataUnavailable
        from sensa.universe import load_overview
        try:
            return {f["cik"] for f in load_overview(self.data_dir)["funds"]}
        except (DataUnavailable, KeyError):
            return set()

    def lookup(self, ticker, **paging):
        from markov.data_providers import DataUnavailable
        t = (ticker or "").strip().upper()
        meta(self.db)                                     # no index yet -> "press Update"
        cusip = self.resolver.cusip(t)
        if cusip is None:
            raise UnknownTicker(f"No 13F holders found for {t or 'that ticker'}")
        try:
            out = self.shares_out.get(t)
        except (DataUnavailable, KeyError, ValueError):
            out = None
        return investors_page(self.db, cusip, t, shares_out=out, top_ciks=self._top_ciks(), live_db=self.live_db, **paging)
