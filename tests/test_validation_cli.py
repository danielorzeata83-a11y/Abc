import numpy as np
import pandas as pd
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
import validate_cli


def _session_index(days=150, bars_per_day=26):
    stamps = []
    for d in pd.bdate_range("2024-01-02", periods=days):
        stamps.extend(pd.date_range(d + pd.Timedelta("9h30m"),
                                    periods=bars_per_day, freq="15min"))
    return pd.DatetimeIndex(stamps)


def _seed(dirpath, symbol):
    idx = _session_index()
    n = len(idx)
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 0.2, size=n))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_cli_runs_and_prints_report(tmp_path, capsys):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    validate_cli.main(["--symbols", "AAA,BBB", "--data-dir", d,
                       "--horizons", "1,5"])
    out = capsys.readouterr().out
    assert "consiliere de investi" in out.lower()
    assert "Ansamblu" in out or "ansamblu" in out.lower()


def test_cli_writes_csv_with_out(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    out_csv = tmp_path / "raport.csv"
    validate_cli.main(["--symbols", "AAA,BBB", "--data-dir", d,
                       "--horizons", "1,5", "--out", str(out_csv)])
    assert out_csv.exists()
    lines = out_csv.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#") and "consiliere de investi" in lines[0].lower()
