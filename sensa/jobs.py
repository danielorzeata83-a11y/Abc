"""One background job at a time with a visible status (shared by the Smart Money and insider builds)."""

import threading

from markov.data_providers import DataUnavailable


class BackgroundJob:
    """Subclasses implement check(force) -> new data or None (already current)."""

    def __init__(self, running_message="working"):
        self._lock = threading.Lock()
        self._thread = None
        self._running_message = running_message
        self._state = {"state": "idle", "message": ""}

    def check(self, force=False):
        raise NotImplementedError

    def state(self):
        with self._lock:
            return dict(self._state)

    def start(self, force=False):
        with self._lock:
            if self._state["state"] == "running":
                return False
            self._state = {"state": "running", "message": self._running_message}
            self._thread = threading.Thread(target=self._run, args=(force,), daemon=True)
            self._thread.start()
            return True

    def _run(self, force):
        try:
            result = self.check(force)
            state = {"state": "done", "message": "up to date" if result is None else "rebuilt"}
        except DataUnavailable as e:
            state = {"state": "error", "message": str(e)}
        except Exception as e:                    # never leave the status stuck on 'running'
            state = {"state": "error", "message": f"unexpected error ({type(e).__name__})"}
        with self._lock:
            self._state = state

    def wait(self, timeout=None):
        t = self._thread
        if t is not None:
            t.join(timeout)
