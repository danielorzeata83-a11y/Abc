"""Daily closing prices per ticker (from a history function), cached in memory and on disk."""

import bisect
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from markov.data_providers import DataUnavailable


class PriceBook:
    def __init__(self, history_fn, cache_path=None, ttl=6 * 3600, clock=time.time, workers=6, retries=0, backoff=1.0, sleep=time.sleep):
        self.history_fn, self.cache_path, self.ttl, self._clock, self.workers = history_fn, cache_path, ttl, clock, workers
        self.retries, self.backoff, self._sleep = retries, backoff, sleep
        self._lock = threading.Lock()
        self._data = {}                       # ticker -> (fetched_at, dates, closes) ; failures: (fetched_at, [], [])
        self._dirty = False
        if cache_path:
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    for t, (at, rows) in json.load(fh).items():
                        self._data[t] = (at, [r[0] for r in rows], [r[1] for r in rows])
            except (OSError, ValueError, TypeError):
                self._data = {}

    def _load(self, t):
        hit = self._data.get(t)
        if hit and self._clock() - hit[0] < self.ttl:
            return hit
        entry = (self._clock(), [], [])
        for attempt in range(self.retries + 1):               # Yahoo throttles bursts: back off before giving up on a ticker
            try:
                bars = self.history_fn(t)
                entry = (self._clock(), [b["time"] for b in bars], [float(b["close"]) for b in bars])
                break
            except DataUnavailable:
                if attempt < self.retries:
                    self._sleep(self.backoff * (2 ** attempt))
            except (ValueError, KeyError):
                break
        with self._lock:
            self._data[t] = entry
            self._dirty = True
        return entry

    def save(self):
        if not self.cache_path or not self._dirty:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
            tmp = self.cache_path + ".tmp"
            with self._lock, open(tmp, "w", encoding="utf-8") as fh:
                json.dump({t: [at, list(zip(d, c))] for t, (at, d, c) in self._data.items() if d}, fh)
            os.replace(tmp, self.cache_path)
            self._dirty = False
        except OSError:
            pass

    def warm(self, tickers):
        todo = [t.upper() for t in dict.fromkeys(tickers)]
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            list(ex.map(self._load, todo))
        self.save()

    def closes(self, ticker):
        _, d, c = self._load(ticker.upper())
        return (list(d), list(c)) if d else None

    def last(self, ticker):
        _, d, c = self._load(ticker.upper())
        return (d[-1], c[-1]) if d else None

    def on_or_before(self, ticker, day):
        _, d, c = self._load(ticker.upper())
        i = bisect.bisect_right(d, day)
        return (d[i - 1], c[i - 1]) if i else None

    def on_or_after(self, ticker, day):
        _, d, c = self._load(ticker.upper())
        i = bisect.bisect_left(d, day)
        return (d[i], c[i]) if i < len(d) else None
