import os

from sensa.envfile import load_env


def test_load_env_sets_missing_and_keeps_existing(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text('# c\nA_KEY="x"\nB_KEY=y\nbad line\n')
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.setenv("B_KEY", "real")
    load_env(str(p))
    assert os.environ["A_KEY"] == "x" and os.environ["B_KEY"] == "real"
    monkeypatch.delenv("A_KEY")


def test_missing_file_is_fine(tmp_path):
    load_env(str(tmp_path / "none"))
