"""File helpers."""

import os
import threading
import time


def replace_file(src, dst, attempts=20, wait=0.5, sleep=time.sleep):
    """os.replace that waits out a short lock: on Windows an antivirus scan or the indexer often holds a freshly
    downloaded file for a few seconds and the rename fails with PermissionError."""
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            sleep(wait)


_locks = {}
_locks_guard = threading.Lock()


def ensure_download(download, url, dest):
    """Download `url` to `dest` once, even when several background jobs ask for the same file at the same time
    (two writers on one `.part` file are what made the rename fail with a sharing violation on Windows)."""
    key = os.path.abspath(dest)
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if os.path.exists(dest):
            return dest
        tmp = f"{dest}.{os.getpid()}.{threading.get_ident()}.part"
        try:
            download(url, tmp)
            replace_file(tmp, dest)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return dest
