"""Forward-only track record of the picks: each day's list is saved, and its return since that day is measured
against the S&P 500 and against the whole scored pool. No hindsight: a snapshot is never edited after the day."""

import json
import os
import threading
from datetime import date, datetime, timezone

NOTE = ("Snapshots overlap in time, so they are not independent observations; a handful of weeks proves little. "
        "Returns are price returns since the snapshot day's close, before costs and taxes.")


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


class TrackRecord:
    def __init__(self, path):
        self.path, self._lock, self._snaps = path, threading.Lock(), []
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    self._snaps = json.load(fh)["snapshots"]
            except (OSError, ValueError, KeyError):
                self._snaps = []

    def snapshots(self):
        with self._lock:
            return [dict(s) for s in self._snaps]

    def record(self, picks):
        day = picks.get("as_of")
        if not day:
            return
        snap = {"date": day, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "stocks": {p["ticker"]: {"weight": p["weight"], "price": p["price"]} for p in picks["stocks"]},
                "etfs": {p["ticker"]: {"weight": p["weight"], "price": p["price"]} for p in picks["etfs"]},
                "pool": picks.get("pool_prices", {"stocks": {}, "etfs": {}})}
        with self._lock:
            self._snaps = sorted([s for s in self._snaps if s["date"] != day] + [snap], key=lambda s: s["date"])
            if self.path:
                os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump({"snapshots": self._snaps}, fh)
                os.replace(tmp, self.path)

    @staticmethod
    def _group(items, pool, prices):
        rets, wsum, acc = [], 0.0, 0.0
        for t, x in items.items():
            last = prices.last(t)
            if last and x["price"]:
                r = last[1] / x["price"] - 1
                rets.append(r)
                wsum += x["weight"]
                acc += x["weight"] * r
        pool_r = [prices.last(t)[1] / p - 1 for t, p in pool.items() if p and prices.last(t)]
        if not rets:
            return None
        return {"priced": len(rets), "of": len(items), "weighted_pct": acc / wsum * 100 if wsum else None,
                "equal_pct": sum(rets) / len(rets) * 100, "pool_pct": sum(pool_r) / len(pool_r) * 100 if pool_r else None}

    def summary(self, prices):
        snaps = self.snapshots()
        spy_last = prices.last("SPY")
        if not snaps or not spy_last:
            return {"snapshots": len(snaps), "rows": [], "aggregate": {}, "as_of": spy_last[0] if spy_last else None,
                    "note": "Collecting: the first results appear a day after the first snapshot. " + NOTE}
        as_of = spy_last[0]
        rows = []
        for s in sorted(snaps, key=lambda s: s["date"], reverse=True):
            age = _days(s["date"], as_of)
            entry = prices.on_or_before("SPY", s["date"]) or prices.on_or_after("SPY", s["date"])
            if age < 1 or not entry:
                continue
            spy = (spy_last[1] / entry[1] - 1) * 100
            row = {"date": s["date"], "age_days": age, "spy_pct": spy}
            for g in ("stocks", "etfs"):
                r = self._group(s[g], s["pool"].get(g, {}), prices)
                if r:
                    r["excess_pct"] = r["weighted_pct"] - spy if r["weighted_pct"] is not None else None
                row[g] = r
            rows.append(row)
        agg = {}
        for g in ("stocks", "etfs"):
            for suffix, min_age in (("", 1), ("_7d", 7), ("_30d", 30)):
                use = [r for r in rows if r[g] and r[g]["excess_pct"] is not None and r["age_days"] >= min_age]
                agg[g + suffix] = {"n": len(use),
                                   "avg_weighted_pct": sum(r[g]["weighted_pct"] for r in use) / len(use) if use else None,
                                   "avg_excess_pct": sum(r[g]["excess_pct"] for r in use) / len(use) if use else None,
                                   "hit_rate_pct": sum(1 for r in use if r[g]["excess_pct"] > 0) / len(use) * 100 if use else None}
        return {"snapshots": len(snaps), "rows": rows, "aggregate": agg, "as_of": as_of, "note": NOTE}
