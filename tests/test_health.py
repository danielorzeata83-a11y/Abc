import pytest

from sensa.health import HealthService


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def svc(jobs=None, probes=None, clock=None, **kw):
    return HealthService(jobs or {}, probes or {}, clock=clock or Clock(), **kw)


def test_jobs_are_reported_with_their_state_message_and_age():
    jobs = {"insiders": lambda: {"state": "done", "message": "", "built_at": "2026-10-26T10:00:00+00:00"},
            "funds": lambda: {"state": "error", "message": "no prices"},
            "lab": lambda: {"state": "running", "message": "loading"},
            "cold": lambda: {"state": "idle", "message": ""}}
    rows = {r["name"]: r for r in svc(jobs).report()["rows"]}
    assert rows["insiders"]["status"] == "ok" and rows["insiders"]["kind"] == "job" and rows["insiders"]["updated"] == "2026-10-26T10:00:00+00:00"
    assert rows["funds"]["status"] == "error" and "no prices" in rows["funds"]["detail"]
    assert rows["lab"]["status"] == "running" and rows["cold"]["status"] == "idle"


def test_a_job_whose_status_call_raises_is_an_error_row_not_a_crash():
    def boom():
        raise RuntimeError("x")
    r = svc({"j": boom}).report()["rows"][0]
    assert r["status"] == "error" and "RuntimeError" in r["detail"]


def test_probes_are_run_once_per_ttl_and_failures_are_shown_with_the_reason():
    calls = []

    def good():
        calls.append("good")
        return True, "200 in 80 ms"

    def bad():
        calls.append("bad")
        return False, "HTTP 403"
    c = Clock()
    s = svc(probes={"Yahoo": good, "SEC": bad}, clock=c, probe_ttl=300)
    rows = {r["name"]: r for r in s.report()["rows"]}
    assert rows["Yahoo"]["status"] == "ok" and rows["SEC"]["status"] == "error" and rows["SEC"]["detail"] == "HTTP 403" and rows["Yahoo"]["kind"] == "source"
    s.report()
    assert sorted(calls) == ["bad", "good"]                  # cached
    c.t += 301
    s.report()
    assert sorted(calls) == ["bad", "bad", "good", "good"]


def test_a_probe_that_raises_or_hangs_is_an_error_row():
    def raises():
        raise OSError("dns")
    import time

    def hangs():
        time.sleep(2)
        return True, "late"
    rows = {r["name"]: r for r in svc(probes={"A": raises, "B": hangs}, probe_timeout=0.2).report()["rows"]}
    assert rows["A"]["status"] == "error" and "dns" in rows["A"]["detail"]
    assert rows["B"]["status"] == "error" and "timed out" in rows["B"]["detail"]


def test_summary_counts_and_secret_presence_flags_never_expose_values():
    s = svc({"j": lambda: {"state": "error", "message": "m"}}, {"p": lambda: (True, "ok")}, keys={"FRED_API_KEY": "secretvalue", "FINNHUB_API_KEY": ""})
    rep = s.report()
    assert rep["summary"] == {"ok": 1, "error": 1, "running": 0, "idle": 0}
    assert rep["keys"] == {"FRED_API_KEY": True, "FINNHUB_API_KEY": False} and "secretvalue" not in str(rep)
