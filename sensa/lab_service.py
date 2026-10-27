"""Portfolio lab service: universes, cached adjusted prices, background runs saved on disk (config, data manifest,
metrics, weights, returns, report) so every result can be audited and re-opened."""

import json
import os
import re
import threading
import time
from datetime import datetime, timezone

from markov.data_providers import DataUnavailable
from sensa.lab_data import load_prices
from sensa.lab_study import DEFAULT_CONFIG, run_study, write_artifacts

DOC_UNIVERSE = ("NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "JPM", "XOM", "JNJ", "CAT", "WMT")
_SYM = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}")
_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
_FILES = ("report.md", "config.json", "data_manifest.json", "metrics.json", "weights.csv", "returns.csv", "result.json")
_ALLOWED = {"window": (60, 1500), "every": (5, 126)}
_GRIDS = ("lam_grid", "kappa_grid", "cvar_lam_grid")
_INT = ("cvar_iters", "perturbations", "seed")


def resolve_universe(kind, overview=None, insiders=None, watchlist=(), custom="", n=12):
    if kind == "document":
        return list(DOC_UNIVERSE)
    if kind == "watchlist":
        return [s for s in dict.fromkeys(watchlist)]
    if kind == "most_held":
        if not overview:
            raise DataUnavailable("The Smart Money overview is not built yet (press Update on the Smart Money page).")
        rows = [s for s in overview["stocks"] if s["kind"] in ("stock", "adr") and not s.get("gone") and not s.get("new_listing")]
        rows.sort(key=lambda s: (s["holders"], s["value"]), reverse=True)
        return [s["ticker"] for s in rows[:n]]
    if kind == "insider_buys":
        if insiders is None:
            raise DataUnavailable("Insider data is not configured (set SEC_CONTACT).")
        tot = {}
        for t in insiders.trades_since(30):
            if t["side"] == "buy":
                tot[t["symbol"]] = tot.get(t["symbol"], 0.0) + t["value"]
        return [s for s, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:n]]
    if kind == "custom":
        syms = [s for s in dict.fromkeys(re.split(r"[\s,;]+", custom.upper().strip())) if _SYM.fullmatch(s)]
        if len(syms) < 2:
            raise ValueError("enter at least two valid tickers")
        return syms[:40]
    raise ValueError(f"unknown universe {kind!r}")


class AdjustedCache:
    """Adjusted daily closes per (ticker, years), kept in memory and on disk for `ttl` seconds."""
    def __init__(self, fetch, path, ttl=12 * 3600, clock=time.time, sleep=time.sleep, retries=2, backoff=1.5, spacing=0.25):
        self.fetch, self.path, self.ttl, self._clock = fetch, path, ttl, clock
        self._sleep, self.retries, self.backoff, self.spacing = sleep, retries, backoff, spacing
        self._lock = threading.Lock()
        try:
            with open(path, encoding="utf-8") as fh:
                self._d = json.load(fh)
        except (OSError, ValueError):
            self._d = {}

    def get(self, ticker, years):
        key = f"{ticker.upper()}:{years}"
        with self._lock:
            hit = self._d.get(key)
        if hit and self._clock() - hit["at"] < self.ttl:
            return [tuple(r) for r in hit["rows"]]
        for attempt in range(self.retries + 1):                  # Yahoo throttles bursts: back off, then give up cleanly
            try:
                rows = self.fetch(ticker.upper(), years)
                break
            except DataUnavailable:
                if attempt == self.retries:
                    raise
                self._sleep(self.backoff * (2 ** attempt))
        self._sleep(self.spacing)
        with self._lock:
            self._d[key] = {"at": self._clock(), "rows": [list(r) for r in rows]}
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(self._d, fh)
                os.replace(tmp, self.path)
            except OSError:
                pass
        return rows


class LabService:
    def __init__(self, data_dir, fetch_adjusted, min_rows=500, overview=None, insiders=None, watchlist=(), benchmark="SPY"):
        self.dir = os.path.join(data_dir, "lab")
        self.cache = AdjustedCache(fetch_adjusted, os.path.join(self.dir, "adjusted_prices.json"))
        self.min_rows, self.overview, self.insiders, self.watchlist, self.benchmark = min_rows, overview, insiders, tuple(watchlist), benchmark
        self._lock, self._thread = threading.Lock(), None
        self._state = {"state": "idle", "message": "", "run_id": None}

    # ---- spec
    def _validate(self, spec):
        years = int(spec.get("years", 10))
        cost = float(spec.get("cost_bps", DEFAULT_CONFIG["cost_bps"]))
        cap = float(spec.get("cap", DEFAULT_CONFIG["cap"]))
        if not 2 <= years <= 20 or not 0 <= cost <= 100 or not 0.05 <= cap <= 1.0:
            raise ValueError("years must be 2-20, cost 0-100 bps, cap 5%-100%")
        cfg = {"cost_bps": cost, "cap": cap}
        for k, v in (spec.get("config") or {}).items():
            if k in _ALLOWED:
                lo, hi = _ALLOWED[k]
                if not lo <= int(v) <= hi:
                    raise ValueError(f"{k} must be {lo}-{hi}")
                cfg[k] = int(v)
            elif k in _GRIDS:
                vals = [float(x) for x in v]
                if not 1 <= len(vals) <= 6 or any(not 0 < x <= 1000 for x in vals):
                    raise ValueError(f"bad {k}")
                cfg[k] = vals
            elif k in _INT:
                cfg[k] = int(v)
        return years, cfg

    def submit(self, spec):
        years, cfg = self._validate(spec)
        tickers = resolve_universe(spec.get("universe", "document"), self.overview() if callable(self.overview) else self.overview,
                                   self.insiders, self.watchlist, spec.get("custom", ""), n=int(spec.get("n", 12)))
        with self._lock:
            if self._state["state"] == "running":
                raise RuntimeError("a lab run is already running")
            rid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + os.urandom(3).hex()
            self._state = {"state": "running", "message": f"loading {len(tickers)} price histories", "run_id": rid}
            self._thread = threading.Thread(target=self._run, args=(rid, tickers, years, cfg, spec.get("universe", "document")), daemon=True)
            self._thread.start()
        return rid

    def _run(self, rid, tickers, years, cfg, universe):
        try:
            prices, manifest = load_prices(tickers, lambda t: self.cache.get(t, years), self.min_rows)
            bench = None
            try:
                bench = __import__("pandas").Series(dict(self.cache.get(self.benchmark, years)))
            except (DataUnavailable, ValueError):
                pass
            self._set(message="running the walk-forward study")
            result = run_study(prices, manifest, cfg, benchmark=bench)
            result["universe_kind"] = universe
            folder = write_artifacts(os.path.join(self.dir, rid), result)
            passed = sum(1 for a in result["acceptance"] if a["pass"])
            with open(os.path.join(folder, "summary.json"), "w", encoding="utf-8") as fh:
                json.dump({"id": rid, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "universe": universe,
                           "tickers": result["tickers"], "passed": passed, "criteria": len(result["acceptance"]),
                           "extended_sharpe": result["test"]["models"]["extended"]["sharpe"],
                           "equal_sharpe": result["test"]["models"]["equal_weight"]["sharpe"]}, fh)
            self._set(state="done", message="")
        except (DataUnavailable, ValueError) as e:
            self._set(state="error", message=str(e)[:300])
        except Exception as e:                              # never leave the status stuck on 'running'
            self._set(state="error", message=f"unexpected error ({type(e).__name__})")

    def _set(self, **kw):
        with self._lock:
            self._state = {**self._state, **kw}

    def wait(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def status(self):
        with self._lock:
            return dict(self._state)

    # ---- stored runs
    def runs(self, limit=30):
        out = []
        try:
            names = sorted(os.listdir(self.dir), reverse=True)
        except OSError:
            return []
        for n in names:
            if _ID.match(n):
                try:
                    with open(os.path.join(self.dir, n, "summary.json"), encoding="utf-8") as fh:
                        out.append(json.load(fh))
                except (OSError, ValueError):
                    continue
        return out[:limit]

    def result(self, rid):
        if not _ID.match(rid or ""):
            raise KeyError(rid)
        try:
            with open(os.path.join(self.dir, rid, "result.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            raise KeyError(rid) from None

    def file(self, rid, name):
        if not _ID.match(rid or "") or name not in _FILES:
            raise KeyError(name)
        path = os.path.join(self.dir, rid, name)
        if not os.path.exists(path):
            raise KeyError(name)
        return path
