"""One page that says what is working: background jobs (state, message, last update) and the free data sources
(probed with a tiny request, cached for a few minutes), plus which optional API keys are set (never their values)."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout


class HealthService:
    def __init__(self, jobs, probes, keys=None, clock=time.time, probe_ttl=300, probe_timeout=8.0):
        self.jobs, self.probes, self.keys = jobs, probes, keys or {}
        self._clock, self.probe_ttl, self.probe_timeout = clock, probe_ttl, probe_timeout
        self._cache, self._lock = {}, threading.Lock()

    def _job(self, name, fn):
        try:
            st = fn() or {}
        except Exception as e:                           # a broken status call must not take the page down
            return {"name": name, "kind": "job", "status": "error", "detail": f"status unavailable ({type(e).__name__})", "updated": None}
        state = st.get("state", "idle")
        status = {"done": "ok", "error": "error", "running": "running"}.get(state, "idle")
        updated = st.get("built_at") or st.get("generated")
        detail = st.get("message") or ("working…" if status == "running" else "")
        return {"name": name, "kind": "job", "status": status, "detail": detail, "updated": updated}

    def _probe(self, name, fn):
        with self._lock:
            hit = self._cache.get(name)
            if hit and self._clock() - hit[0] < self.probe_ttl:
                return hit[1]
        ex = ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(fn)
        try:
            ok, detail = fut.result(timeout=self.probe_timeout)
            row = {"name": name, "kind": "source", "status": "ok" if ok else "error", "detail": detail, "updated": None}
        except FutureTimeout:
            row = {"name": name, "kind": "source", "status": "error", "detail": f"timed out after {self.probe_timeout:g} s", "updated": None}
        except Exception as e:
            row = {"name": name, "kind": "source", "status": "error", "detail": f"{type(e).__name__}: {e}"[:160], "updated": None}
        ex.shutdown(wait=False)
        with self._lock:
            self._cache[name] = (self._clock(), row)
        return row

    def report(self):
        rows = [self._job(n, f) for n, f in self.jobs.items()]
        with ThreadPoolExecutor(max_workers=max(1, len(self.probes))) as ex:
            rows += list(ex.map(lambda kv: self._probe(*kv), self.probes.items()))
        summary = {k: sum(1 for r in rows if r["status"] == k) for k in ("ok", "error", "running", "idle")}
        return {"rows": rows, "summary": summary, "keys": {k: bool(v) for k, v in self.keys.items()}}
