"""Off-exchange (ATS, "dark pool") volume from FINRA's OTC Transparency weekly data.

Free and public, but weekly and delayed about three weeks: it is aggregate volume per stock and venue,
not individual prints."""

import json
import time
from datetime import date, timedelta

from markov.data_providers import DataUnavailable

URL = "https://api.finra.org/data/group/otcMarket/name/weeklySummary"
_TIERS = ("T1", "T2")            # NMS Tier 1 (large caps / major ETPs) and Tier 2
_PROBES = 8                      # how many weeks back to look for the newest published week


def _flt(field, value):
    return {"compareType": "EQUAL", "fieldName": field, "fieldValue": value}


class DarkPool:
    def __init__(self, post, today=date.today, clock=time.monotonic, ttl=6 * 3600):
        self.post, self.today, self.clock, self.ttl = post, today, clock, ttl
        self._cache = {}

    def _cached(self, key, load):
        hit = self._cache.get(key)
        if hit and self.clock() - hit[0] < self.ttl:
            return hit[1]
        val = load()
        self._cache[key] = (self.clock(), val)
        return val

    def _query(self, week, kind, tier=None, symbol=None, limit=1000):
        filters = [_flt("weekStartDate", week), _flt("summaryTypeCode", kind)]
        payload = {"limit": limit, "compareFilters": filters}
        if tier:
            filters.append(_flt("tierIdentifier", tier))
            payload["sortFields"] = ["-totalWeeklyShareQuantity"]      # FINRA only sorts when both partition keys are EQUAL
        if symbol:
            filters.append(_flt("issueSymbolIdentifier", symbol))
        text = self.post(URL, payload, {"Accept": "application/json"})
        return json.loads(text) if text and text.strip() else []

    def latest_week(self):
        def find():
            monday = self.today() - timedelta(days=self.today().weekday())
            for back in range(2, 2 + _PROBES):                        # data trails by roughly two to three weeks
                week = (monday - timedelta(weeks=back - 2) - timedelta(weeks=2)).isoformat()
                if self._query(week, "ATS_W_SMBL", tier="T1", limit=1):
                    return week
            raise DataUnavailable("no recent FINRA ATS weekly data found")
        return self._cached(("week",), find)

    def _symbols(self, week):
        rows = []
        for tier in _TIERS:
            rows += self._query(week, "ATS_W_SMBL", tier=tier)
        return {r["issueSymbolIdentifier"]: r for r in rows if r.get("issueSymbolIdentifier")}

    def _firms(self, week):
        """Per-ATS totals for a week (a few dozen rows). Tier 1 only: FINRA publishes Tier 2 about two weeks
        later, so mixing tiers would make the newest weeks look like a collapse."""
        return self._cached(("firms", week), lambda: self._query(week, "ATS_W_FIRM", tier="T1"))

    def _totals(self, week):
        rows = self._firms(week)
        if not rows:
            return None
        return {"week": week, "shares": sum(r["totalWeeklyShareQuantity"] for r in rows),
                "trades": sum(r["totalWeeklyTradeCount"] for r in rows)}

    def overview(self, top=50):
        def load():
            week = self.latest_week()
            w = date.fromisoformat(week)
            prev_week = (w - timedelta(weeks=1)).isoformat()
            cur, prev = self._symbols(week), self._symbols(prev_week)
            ranked = sorted(cur.values(), key=lambda r: r["totalWeeklyShareQuantity"], reverse=True)[:top]
            rows = []
            for r in ranked:
                sh, tr = r["totalWeeklyShareQuantity"], r["totalWeeklyTradeCount"]
                p = prev.get(r["issueSymbolIdentifier"])
                rows.append({"symbol": r["issueSymbolIdentifier"], "name": r.get("issueName") or "", "tier": r.get("tierIdentifier"),
                             "shares": sh, "trades": tr, "avg_trade": round(sh / tr, 2) if tr else None,
                             "notional": r.get("totalNotionalSum"),
                             "change_pct": round((sh - p["totalWeeklyShareQuantity"]) / p["totalWeeklyShareQuantity"] * 100, 2)
                             if p and p["totalWeeklyShareQuantity"] else None})
            history = [t for t in (self._totals((w - timedelta(weeks=i)).isoformat()) for i in range(11, -1, -1)) if t]
            by_mpid = {}
            for r in self._firms(week):
                v = by_mpid.setdefault(r.get("MPID") or r.get("marketParticipantName") or "?",
                                       {"mpid": r.get("MPID"), "name": r.get("marketParticipantName") or r.get("MPID") or "",
                                        "shares": 0.0, "trades": 0})
                v["shares"] += r["totalWeeklyShareQuantity"]
                v["trades"] += r["totalWeeklyTradeCount"]
            tot = sum(v["shares"] for v in by_mpid.values()) or 1.0
            venues = [{**v, "share_pct": round(v["shares"] / tot * 100, 2)}
                      for v in sorted(by_mpid.values(), key=lambda v: v["shares"], reverse=True)[:12]]
            cur_t = next((t for t in history if t["week"] == week), None)
            prev_t = next((t for t in history if t["week"] == prev_week), None)
            return {"week": week, "prev_week": prev_week, "top": rows, "venues": venues,
                    "tier_note": "Totals, venues and history cover NMS Tier 1 (S&P 500, Russell 1000 and major ETFs); "
                                 "Tier 2 is published later and left out so weeks stay comparable.",
                    "total_shares": cur_t["shares"] if cur_t else None, "total_trades": cur_t["trades"] if cur_t else None,
                    "total_change_pct": round((cur_t["shares"] - prev_t["shares"]) / prev_t["shares"] * 100, 2)
                    if cur_t and prev_t and prev_t["shares"] else None,
                    "history": [{"week": t["week"], "shares": t["shares"], "trades": t["trades"]} for t in history]}
        return self._cached(("overview", top), load)

    def symbol(self, sym):
        s = sym.upper()

        def load():
            week = self.latest_week()
            rows = sorted(self._query(week, "ATS_W_SMBL_FIRM", symbol=s), key=lambda r: r["totalWeeklyShareQuantity"], reverse=True)
            total = sum(r["totalWeeklyShareQuantity"] for r in rows) or 1.0
            return {"symbol": s, "week": week,
                    "venues": [{"mpid": r.get("MPID"), "name": r.get("marketParticipantName") or r.get("MPID") or "",
                                "shares": r["totalWeeklyShareQuantity"], "trades": r["totalWeeklyTradeCount"],
                                "share_pct": round(r["totalWeeklyShareQuantity"] / total * 100, 2)} for r in rows]}
        return self._cached(("symbol", s), load)
