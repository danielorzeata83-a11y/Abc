"""Valuation and quality from SEC's XBRL company facts (free): trailing-twelve-month revenue, profit, EPS and margins,
growth over the last fiscal year, return on equity and leverage. TTM = last fiscal year + this year to date - the same
period a year earlier. Only companies that file XBRL with the SEC have data (not ETFs or most foreign issuers)."""

import json
import os
import threading
import time
from datetime import date

from markov.data_providers import DataUnavailable

URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_REV = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet")


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _entries(j, names, unit):
    ns = (j.get("facts") or {}).get("us-gaap") or {}
    for n in names:
        rows = ((ns.get(n) or {}).get("units") or {}).get(unit) or []
        if rows:
            best = {}
            for r in rows:                                          # restatements: the latest filing of a period wins
                k = (r.get("start"), r["end"])
                if k not in best or r.get("filed", "") > best[k].get("filed", ""):
                    best[k] = r
            return list(best.values())
    return []


def _ttm(rows):
    """(ttm value, period end, previous fiscal year value, filed, last fiscal year value) from duration facts, or None."""
    dur = [r for r in rows if r.get("start")]
    annual = [r for r in dur if 340 <= _days(r["start"], r["end"]) <= 380]
    if not annual:
        return None
    a = max(annual, key=lambda r: r["end"])
    prev = next((r for r in annual if 350 <= _days(r["end"], a["end"]) <= 380), None)
    ytd = [r for r in dur if r["end"] > a["end"] and 60 <= _days(r["start"], r["end"]) <= 300]
    value, end, filed = a["val"], a["end"], a.get("filed")
    if ytd:
        y = max(ytd, key=lambda r: (r["end"], _days(r["start"], r["end"])))
        dy = _days(y["start"], y["end"])
        p = next((r for r in dur if r is not y and abs(_days(r["end"], y["end"]) - 365) <= 12 and abs(_days(r["start"], r["end"]) - dy) <= 12), None)
        if p:
            value, end, filed = a["val"] + y["val"] - p["val"], y["end"], y.get("filed")
    return value, end, (prev["val"] if prev else None), filed, a["val"]


def _latest(rows):
    return max(rows, key=lambda r: r["end"])["val"] if rows else None


def parse_company_facts(j):
    if not j or not j.get("facts"):
        return None
    rev = _ttm(_entries(j, _REV, "USD"))
    ni = _ttm(_entries(j, ("NetIncomeLoss",), "USD"))
    op = _ttm(_entries(j, ("OperatingIncomeLoss",), "USD"))
    gp = _ttm(_entries(j, ("GrossProfit",), "USD"))
    eps = _ttm(_entries(j, ("EarningsPerShareDiluted", "EarningsPerShareBasic"), "USD/shares"))
    if not (rev or ni or eps):
        return None
    equity = _latest(_entries(j, ("StockholdersEquity",), "USD"))
    debt = _latest(_entries(j, ("LongTermDebt", "LongTermDebtNoncurrent"), "USD"))
    cur = _latest(_entries(j, ("DebtCurrent",), "USD"))
    if debt is not None and cur:
        debt += cur
    cash = _latest(_entries(j, ("CashAndCashEquivalentsAtCarryingValue",), "USD"))
    revv = rev[0] if rev else None
    pct = lambda a, b: a / b * 100 if a is not None and b else None
    ends = [x[1] for x in (rev, ni, eps, op) if x]
    return {"revenue_ttm": revv, "revenue_growth_pct": (rev[4] / rev[2] - 1) * 100 if rev and rev[2] else None,
            "net_income_ttm": ni[0] if ni else None, "eps_ttm": eps[0] if eps else None, "op_income_ttm": op[0] if op else None,
            "op_margin_pct": pct(op[0], revv) if op else None, "net_margin_pct": pct(ni[0], revv) if ni else None,
            "gross_margin_pct": pct(gp[0], revv) if gp else None, "roe_pct": pct(ni[0], equity) if ni and equity and equity > 0 else None,
            "debt_to_equity": debt / equity if debt is not None and equity and equity > 0 else None,
            "net_debt": debt - cash if debt is not None and cash is not None else None, "equity": equity, "debt": debt, "cash": cash,
            "period_end": max(ends) if ends else None, "filed": max((x[3] for x in (rev, ni, eps) if x and x[3]), default=None)}


class Fundamentals:
    def __init__(self, fetch_sec, cik_fn, cache_path=None, ttl=7 * 86400, clock=time.time):
        self.fetch, self.cik_fn, self.cache_path, self.ttl, self._clock = fetch_sec, cik_fn, cache_path, ttl, clock
        self._lock, self._d = threading.Lock(), {}
        if cache_path:
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    self._d = json.load(fh)
            except (OSError, ValueError):
                self._d = {}

    def _metrics(self, t):
        with self._lock:
            hit = self._d.get(t)
        if hit and self._clock() - hit["at"] < self.ttl:
            return hit["m"]
        cik = self.cik_fn(t)
        if not cik:
            return None
        try:
            m = parse_company_facts(json.loads(self.fetch(URL.format(cik=cik))))
        except (DataUnavailable, ValueError, KeyError):
            return None
        if m is not None:
            with self._lock:
                self._d[t] = {"at": self._clock(), "m": m}
                if self.cache_path:
                    try:
                        os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
                        tmp = self.cache_path + ".tmp"
                        with open(tmp, "w", encoding="utf-8") as fh:
                            json.dump(self._d, fh)
                        os.replace(tmp, self.cache_path)
                    except OSError:
                        pass
        return m

    def get(self, ticker, price=None):
        m = self._metrics(ticker.upper())
        if m is None:
            return None
        out = dict(m)
        eps = m.get("eps_ttm")
        out["pe"] = price / eps if price and eps and eps > 0 else None
        out["earnings_yield_pct"] = eps / price * 100 if price and eps is not None else None
        out["market_cap"] = None
        return out
