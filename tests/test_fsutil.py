import os

import pytest

from sensa import fsutil


def test_replace_retries_a_locked_file(tmp_path, monkeypatch):
    src, dst = tmp_path / "a.part", tmp_path / "a"
    src.write_text("x")
    real, calls = os.replace, []

    def flaky(s, d):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("locked")
        real(s, d)
    monkeypatch.setattr(fsutil.os, "replace", flaky)
    fsutil.replace_file(str(src), str(dst), sleep=lambda s: None)
    assert dst.read_text() == "x" and len(calls) == 3


def test_replace_gives_up_after_the_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil.os, "replace", lambda s, d: (_ for _ in ()).throw(PermissionError("locked")))
    with pytest.raises(PermissionError):
        fsutil.replace_file("a", "b", attempts=3, sleep=lambda s: None)


def test_ensure_download_fetches_once_for_concurrent_callers(tmp_path):
    import threading
    import time
    dest, n = str(tmp_path / "z.zip"), []

    def dl(url, path):
        n.append(1)
        time.sleep(0.1)
        open(path, "w").write("data")
    ts = [threading.Thread(target=fsutil.ensure_download, args=(dl, "u", dest)) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(n) == 1 and open(dest).read() == "data"
    assert os.listdir(tmp_path) == ["z.zip"]
