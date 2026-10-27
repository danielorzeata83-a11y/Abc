import threading

import pytest

from markov.data_providers import DataUnavailable
from sensa.throttle import ThrottledFetch


class Clock:
    def __init__(self):
        self.t, self.sleeps = 0.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def test_requests_are_spaced_by_the_minimum_interval_across_calls():
    c, calls = Clock(), []
    f = ThrottledFetch(lambda url, headers=None: calls.append(url) or "ok", min_interval=0.5, clock=c.now, sleep=c.sleep)
    for i in range(3):
        f(f"u{i}")
    assert calls == ["u0", "u1", "u2"] and c.sleeps == [0.5, 0.5]                    # the first call is immediate


def test_a_failed_request_is_retried_with_growing_pauses_and_then_raised():
    c, n = Clock(), [0]

    def flaky(url, headers=None):
        n[0] += 1
        if n[0] < 3:
            raise DataUnavailable("fetch failed (HTTPError)")
        return "body"
    f = ThrottledFetch(flaky, min_interval=0.0, retries=2, backoff=2.0, clock=c.now, sleep=c.sleep)
    assert f("u") == "body" and n[0] == 3 and c.sleeps == [2.0, 4.0]

    def dead(url, headers=None):
        raise DataUnavailable("blocked")
    with pytest.raises(DataUnavailable, match="blocked"):
        ThrottledFetch(dead, min_interval=0.0, retries=1, backoff=1.0, clock=c.now, sleep=c.sleep)("u")


def test_threads_share_one_schedule():
    stamps, lock = [], threading.Lock()
    import time
    f = ThrottledFetch(lambda url, headers=None: stamps.append(time.monotonic()) or "ok", min_interval=0.05)
    ts = [threading.Thread(target=f, args=(f"u{i}",)) for i in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    stamps.sort()
    assert all(b - a >= 0.04 for a, b in zip(stamps, stamps[1:]))
