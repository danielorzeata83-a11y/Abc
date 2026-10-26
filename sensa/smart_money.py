"""Keeps the cross-fund Smart Money overview current.

`check()` looks at SEC's list of Form 13F data sets and rebuilds only when a newer quarter exists;
`start()` does the same in a background thread (page button / daily loop) with a visible status.
A new quarter produces one summary message for `notify` (e.g. Telegram)."""

import threading

from markov.data_providers import DataUnavailable
from sensa.universe import load_overview, refresh_overview


def _money(v):
    a = abs(v)
    s = f"${a / 1e12:.2f}T" if a >= 1e12 else f"${a / 1e9:.1f}B" if a >= 1e9 else f"${a / 1e6:.0f}M"
    return ("-" if v < 0 else "+") + s


def format_summary(o, n=5):
    """Plain-text digest of what moved inside the cohort (stocks/ADRs only; ETFs and vanished names left out)."""
    eq = [s for s in o["stocks"] if s["kind"] in ("stock", "adr")]
    st = [s for s in eq if not s["gone"] and not s.get("new_listing")]
    lines = [f"Smart Money top {o['cohort']}: {o['quarter']} vs {o['prev_quarter']} (${o['total_aum'] / 1e12:.1f}T reported)"]

    def block(title, rows, fmt):
        if rows:
            lines.append(title)
            lines.extend("  " + fmt(s) for s in rows[:n])
    block("Most held:", sorted(st, key=lambda s: (s["holders"], s["value"]), reverse=True),
          lambda s: f"{s['ticker']} {s['holders']}/{o['cohort']} funds ({s['holders'] - s['holders_prev']:+d})")
    block("Biggest active buying:", sorted(st, key=lambda s: -s["active_flow"]),
          lambda s: f"{s['ticker']} {_money(s['active_flow'])}, {s['new']} new")
    block("Biggest active selling:", sorted(st, key=lambda s: s["active_flow"]),
          lambda s: f"{s['ticker']} {_money(s['active_flow'])}, {s['exited']} exited")
    block("Most new positions:", sorted((s for s in st if s["new"]), key=lambda s: -s["new"]),
          lambda s: f"{s['ticker']} +{s['new']} funds")
    block("New to the group (IPO, spin-off, CUSIP change):", sorted((s for s in eq if s.get("new_listing")),
                                                                      key=lambda s: -s["holders"]),
          lambda s: f"{s['ticker']} {s['holders']}/{o['cohort']} funds")
    return "\n".join(lines)[:3500]


class OverviewService:
    def __init__(self, data_dir, fetch_listing, download, figi, top=100, notify=None):
        self.data_dir, self.fetch_listing, self.download = data_dir, fetch_listing, download
        self.figi, self.top, self.notify = figi, top, notify
        self._lock = threading.Lock()
        self._thread = None
        self._state = {"state": "idle", "message": ""}

    def overview(self):
        try:
            return load_overview(self.data_dir)
        except DataUnavailable:
            raise DataUnavailable("No Smart Money overview yet. Press Update to build it from SEC data "
                                  "(a few minutes the first time).") from None

    def status(self):
        with self._lock:
            st = dict(self._state)
        try:
            o = load_overview(self.data_dir)
            st.update(period=o["period"], quarter=o["quarter"], built_at=o["generated"])
        except DataUnavailable:
            st.update(period=None, quarter=None, built_at=None)
        return st

    def check(self, force=False):
        """Rebuild if SEC published a newer quarter. Returns the new overview or None (already current)."""
        o = refresh_overview(self.data_dir, self.fetch_listing(), self.download, self.figi, top=self.top, force=force)
        if o is not None and self.notify is not None:
            try:
                self.notify(format_summary(o))
            except Exception:                    # a broken channel must not undo a successful build
                pass
        return o

    def start(self, force=False):
        with self._lock:
            if self._state["state"] == "running":
                return False
            self._state = {"state": "running", "message": "downloading and processing SEC data sets"}
            self._thread = threading.Thread(target=self._run, args=(force,), daemon=True)
            self._thread.start()
            return True

    def _run(self, force):
        try:
            o = self.check(force)
            state = {"state": "done", "message": "up to date" if o is None else "rebuilt"}
        except DataUnavailable as e:
            state = {"state": "error", "message": str(e)}
        except Exception as e:                   # never leave the status stuck on 'running'
            state = {"state": "error", "message": f"unexpected error ({type(e).__name__})"}
        with self._lock:
            self._state = state

    def wait(self, timeout=None):
        t = self._thread
        if t is not None:
            t.join(timeout)
