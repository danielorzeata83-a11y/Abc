"""One shared pace for every Yahoo request. Several background jobs price hundreds of tickers at the same time; without
a common limit Yahoo answers 429 and tickers silently go missing. Requests are spaced across all threads, and a failed one
is retried a couple of times with growing pauses before the error is raised."""

import threading
import time

from markov.data_providers import DataUnavailable


class ThrottledFetch:
    def __init__(self, fetch, min_interval=0.35, retries=2, backoff=2.0, clock=time.monotonic, sleep=time.sleep):
        self.fetch, self.min_interval, self.retries, self.backoff = fetch, min_interval, retries, backoff
        self._clock, self._sleep, self._lock, self._next = clock, sleep, threading.Lock(), 0.0

    def _wait(self):
        with self._lock:
            now = self._clock()
            wait = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.min_interval
        if wait:
            self._sleep(wait)

    def __call__(self, url, headers=None):
        for attempt in range(self.retries + 1):
            self._wait()
            try:
                return self.fetch(url, headers) if headers is not None else self.fetch(url)
            except DataUnavailable:
                if attempt == self.retries:
                    raise
                self._sleep(self.backoff * (2 ** attempt))
