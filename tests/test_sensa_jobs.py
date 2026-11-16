import threading

from markov.data_providers import DataUnavailable
from sensa.jobs import BackgroundJob


class Job(BackgroundJob):
    def __init__(self, fn):
        super().__init__("working")
        self.fn = fn

    def check(self, force=False):
        return self.fn(force)


def test_start_runs_once_at_a_time_and_reports_done():
    gate = threading.Event()
    job = Job(lambda force: gate.wait(5) or "built")
    assert job.start() is True and job.state()["state"] == "running" and job.start() is False
    gate.set()
    job.wait(5)
    assert job.state() == {"state": "done", "message": "rebuilt"}


def test_no_news_is_reported_as_up_to_date():
    job = Job(lambda force: None)
    job.start()
    job.wait(5)
    assert job.state() == {"state": "done", "message": "up to date"}


def test_failures_become_error_status_and_allow_a_retry():
    def boom(force):
        raise DataUnavailable("network down")
    job = Job(boom)
    job.start(force=True)
    job.wait(5)
    assert job.state()["state"] == "error" and "network down" in job.state()["message"]
    assert job.start() is True


def test_unexpected_exceptions_never_leave_the_job_stuck_running():
    def bug(force):
        raise KeyError("x")
    job = Job(bug)
    job.start()
    job.wait(5)
    assert job.state()["state"] == "error" and "KeyError" in job.state()["message"]
