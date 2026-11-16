"""Follow 13F managers and get a signal when one files a new report.

State lives in one small JSON file (following, seen filings, events). A new filing
is compared with the previous quarter; positions added / removed / increased /
reduced become an event, which is stored first and then sent to `notify(text)`.
A failed notification is retried on the next check; a filing that could not be
downloaded is not marked seen, so it is retried too. 13F is quarterly: signals
arrive when SEC publishes the filing, not in real time."""

import json
import os
import threading

from markov.data_providers import DataUnavailable
from sensa.thirteenf import changes

_MAX_EVENTS = 500
_MAX_CHANGES = 25
_TEXT_LIMIT = 3900          # Telegram messages are capped at 4096 characters


def _money(v):
    v = abs(v)
    return f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v:,.0f}"


def format_event(ev):
    c = ev["counts"]
    head = (f"{ev['name']} - {ev['quarter']} {ev['form']}"
            f"{' (amended)' if ev.get('amended') else ''}, filed {ev['filed']}\n"
            f"{c['new']} new, {c['exited']} exited, {c['increased']} increased, {c['reduced']} reduced")
    sym = {"new": "NEW", "exited": "EXITED", "increased": "UP", "reduced": "DOWN"}
    lines = [head]
    for ch in ev["changes"]:
        delta = ch["shares_now"] - ch["shares_prev"]
        size = _money(ch["value_prev"] if ch["type"] == "exited" else ch["value_now"])
        lines.append(f"{sym[ch['type']]} {ch['ticker']} {size} ({delta:+,.0f} sh)")
    text = "\n".join(lines)
    return text if len(text) <= _TEXT_LIMIT else text[:_TEXT_LIMIT - 20].rsplit("\n", 1)[0] + "\n... (more)"


class Watcher:
    def __init__(self, thirteenf, figi, path, notify=None, now=None):
        self.sec, self.figi, self.path, self.notify = thirteenf, figi, path, notify
        self.now = now or (lambda: __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z")
        self.state = self._load()
        self._lock = threading.RLock()      # background loop and 'Check now' may overlap

    # ---- persistence -------------------------------------------------
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                s = json.load(fh)
            return {"following": dict(s.get("following", {})), "seen": dict(s.get("seen", {})),
                    "events": list(s.get("events", []))}
        except (OSError, ValueError, AttributeError, TypeError):
            return {"following": {}, "seen": {}, "events": []}

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh)
        os.replace(tmp, self.path)

    # ---- public API --------------------------------------------------
    def following(self):
        return [{"cik": k, **v} for k, v in self.state["following"].items()]

    def events(self):
        return list(reversed(self.state["events"]))            # newest first

    def follow(self, cik, baseline=True):
        with self._lock:
            self._follow(cik, baseline)

    def _follow(self, cik, baseline):
        cik = f"{int(cik):010d}"
        name = cik
        if baseline:
            f = self.sec.filer(cik)             # raises DataUnavailable if SEC is unreachable
            name = f["name"]
            self.state["seen"][cik] = [x["accession"] for x in f["filings"]]
        self.state["following"][cik] = {"name": name, "since": self.now()}
        self._save()

    def unfollow(self, cik):
        with self._lock:
            self._unfollow(cik)

    def _unfollow(self, cik):
        cik = f"{int(cik):010d}"
        self.state["following"].pop(cik, None)
        self.state["seen"].pop(cik, None)
        self._save()

    def check(self):
        """Look for new filings of every followed fund; return the events created now."""
        with self._lock:
            return self._check()

    def _check(self):
        created = []
        for cik in list(self.state["following"]):
            try:
                created += self._check_one(cik)
            except DataUnavailable:
                continue                         # one unreachable fund must not stop the rest
        self._retry_notifications()
        return created

    # ---- internals ---------------------------------------------------
    @staticmethod
    def _previous(filings, f):
        if f["form"] != "13F-HR":                # an amendment restates its own period's original
            orig = [x for x in filings if x["period"] == f["period"] and x["form"] == "13F-HR"
                    and x["accession"] != f["accession"]]
            if orig:
                return max(orig, key=lambda x: x["filed"])
        older = [x for x in filings if x["period"] < f["period"]]
        if not older:
            return None
        last_period = max(x["period"] for x in older)
        return max((x for x in older if x["period"] == last_period), key=lambda x: x["filed"])

    def _check_one(self, cik):
        filer = self.sec.filer(cik)
        self.state["following"][cik]["name"] = filer["name"]
        seen = set(self.state["seen"].get(cik, []))
        fresh = sorted((f for f in filer["filings"] if f["accession"] not in seen),
                       key=lambda f: (f["period"], f["filed"]))
        events = []
        for f in fresh:
            prev = self._previous(filer["filings"], f)
            ev = None
            if prev is not None:
                cur_rows = self.sec.holdings(cik, f["accession"], f["filed"])      # may raise -> retried later
                prev_rows = self.sec.holdings(cik, prev["accession"], prev["filed"])
                diff = changes(cur_rows, prev_rows)
                if diff:
                    ev = self._event(cik, filer, f, diff)
            if ev:
                self.state["events"] = (self.state["events"] + [ev])[-_MAX_EVENTS:]
                events.append(ev)
            seen.add(f["accession"])
            self.state["seen"][cik] = sorted(seen)
            self._save()
        return events

    def _event(self, cik, filer, f, diff):
        top = diff[:_MAX_CHANGES]
        try:
            tick = self.figi.lookup([c["cusip"] for c in top]) if self.figi else {}
        except DataUnavailable:
            tick = {}
        counts = {k: sum(1 for c in diff if c["type"] == k) for k in ("new", "exited", "increased", "reduced")}
        return {"id": f"{cik}-{f['accession']}", "cik": cik, "name": filer["name"], "quarter": f["quarter"],
                "form": f["form"], "amended": f["form"] != "13F-HR", "filed": f["filed"],
                "accession": f["accession"], "detected_at": self.now(), "counts": counts,
                "changes": [{**c, "ticker": tick.get(c["cusip"]) or c["issuer"][:12].strip()} for c in top],
                "notified": False}

    def _retry_notifications(self):
        if self.notify is None:
            return
        dirty = False
        for ev in self.state["events"]:
            if ev.get("notified"):
                continue
            try:
                self.notify(format_event(ev))
                ev["notified"] = True
            except Exception:                     # a broken channel must never stop the checker
                pass
            dirty = True
        if dirty:
            self._save()
