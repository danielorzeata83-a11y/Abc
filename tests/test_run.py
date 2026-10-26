import run


def test_load_env_reads_pairs_skips_comments_and_never_overrides_the_real_environment(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# keys\nSEC_CONTACT=me@example.com\nFRED_API_KEY = "abc"\n\nBAD LINE\nKEEP=file\n', encoding="utf-8")
    monkeypatch.setenv("KEEP", "real")
    monkeypatch.delenv("SEC_CONTACT", raising=False)
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    run.load_env(str(f))
    import os
    assert os.environ["SEC_CONTACT"] == "me@example.com" and os.environ["FRED_API_KEY"] == "abc" and os.environ["KEEP"] == "real"


def test_load_env_without_a_file_is_fine(tmp_path):
    run.load_env(str(tmp_path / "missing"))


def test_save_env_value_appends_and_replaces(tmp_path):
    f = tmp_path / ".env"
    run.save_env_value(str(f), "SEC_CONTACT", "a@b.co")
    run.save_env_value(str(f), "FRED_API_KEY", "k")
    run.save_env_value(str(f), "SEC_CONTACT", "c@d.co")
    assert f.read_text().splitlines() == ["SEC_CONTACT=c@d.co", "FRED_API_KEY=k"]
