"""The daily brief: what changed since the last look, in one list. Sources: picks that entered or left the top
lists, insider cluster buys, House purchases by several members, filings of followed funds, plus extra sections
(your portfolio). New items are flagged and each one is pushed to Telegram only once."""

import json
import os
import threading
from datetime import datetime, timezone


def _money(v):
    return f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1e3:.0f}k"


def build_brief(picks, prev_snapshot, insider_trades, politician_trades, fund_events, extra=(), today=None):
    day = picks.get("as_of") or today or datetime.now(timezone.utc).date().isoformat()
    sections = []
    items = []
    if prev_snapshot:
        for g, label in (("stocks", "stocks"), ("etfs", "ETFs")):
            now = {p["ticker"]: p for p in picks.get(g, [])}
            old = set(prev_snapshot.get(g, {}))
            kind = "stock" if g == "stocks" else "etf"
            for t, p in sorted(now.items(), key=lambda kv: kv[1]["rank"]):
                if t not in old:
                    items.append({"key": f"picks:in:{kind}:{t}", "ticker": t, "severity": "info",
                                  "text": f"{t} ({p['name']}) entered the top {len(now)} {label} at rank {p['rank']}"})
            for t in sorted(old - set(now)):
                items.append({"key": f"picks:out:{kind}:{t}", "ticker": t, "severity": "warn", "text": f"{t} left the top {len(now)} {label}"})
    sections.append({"id": "picks", "title": "Picks: who entered or left the lists", "items": items})

    by = {}
    for t in insider_trades:
        if t["side"] == "buy":
            x = by.setdefault(t["symbol"], {"owners": set(), "value": 0.0, "last": ""})
            x["owners"].add(t["owner"])
            x["value"] += t["value"]
            x["last"] = max(x["last"], t["date"])
    ins = [{"key": f"ins:{s}:{x['last']}", "ticker": s, "severity": "info",
            "text": f"{s}: {len(x['owners'])} insiders bought {_money(x['value'])} (last on {x['last']})"}
           for s, x in sorted(by.items(), key=lambda kv: -kv[1]["value"]) if len(x["owners"]) >= 3 and x["value"] >= 100_000]
    sections.append({"id": "insiders", "title": "Insider cluster buys (last 2 weeks)", "items": ins})

    pb = {}
    for t in politician_trades:
        if t.get("ticker") and t["type"] == "purchase":
            x = pb.setdefault(t["ticker"], {"m": set(), "last": ""})
            x["m"].add(t["member"])
            x["last"] = max(x["last"], t["date"])
    pol = [{"key": f"pol:{s}:{x['last']}", "ticker": s, "severity": "info", "text": f"{s}: {len(x['m'])} House members bought (last on {x['last']})"}
           for s, x in sorted(pb.items(), key=lambda kv: -len(kv[1]["m"])) if len(x["m"]) >= 2]
    sections.append({"id": "politicians", "title": "House purchases by several members", "items": pol})

    funds = [{"key": f"fund:{e['id']}", "ticker": None, "severity": "info", "cik": e.get("cik"),
              "text": f"{e['name']} filed {e['quarter']}: {e['counts']['new']} new, {e['counts']['exited']} exited, "
                      f"{e['counts']['increased']} increased, {e['counts']['reduced']} reduced positions"} for e in fund_events]
    sections.append({"id": "funds", "title": "Funds you follow", "items": funds})
    for x in extra:
        sections.append({"id": x["section"], "title": x["title"], "items": list(x["items"])})
    return {"date": day, "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sections": sections}


class BriefService:
    def __init__(self, path, keep=60):
        self.path, self.keep, self._lock = path, keep, threading.Lock()
        self._d = {"history": [], "seen": [], "notified": []}
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    self._d.update(json.load(fh))
            except (OSError, ValueError):
                pass

    def _save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._d, fh)
        os.replace(tmp, self.path)

    def store(self, brief):
        with self._lock:
            seen = set(self._d["seen"])
            n = 0
            for s in brief["sections"]:
                for it in s["items"]:
                    it["new"] = it["key"] not in seen
                    n += it["new"]
                    seen.add(it["key"])
            brief["new_count"] = n
            self._d["seen"] = sorted(seen)[-5000:]
            self._d["history"] = (self._d["history"] + [brief])[-self.keep:]
            self._save()
            return brief

    def notify(self, brief, send):
        with self._lock:
            done = set(self._d["notified"])
            lines = [f"• {it['text']}" for s in brief["sections"] for it in s["items"] if it["key"] not in done and it.get("new", True)]
            keys = [it["key"] for s in brief["sections"] for it in s["items"] if it["key"] not in done and it.get("new", True)]
        if not lines:
            return False
        try:
            send(f"Daily brief {brief['date']}\n" + "\n".join(lines)[:3400])
        except Exception:                                  # a broken channel must never break the job; retried next run
            return False
        with self._lock:
            self._d["notified"] = sorted(done | set(keys))[-5000:]
            self._save()
        return True

    def history(self):
        with self._lock:
            return list(self._d["history"])

    def latest(self):
        h = self.history()
        return h[-1] if h else None
