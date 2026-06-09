import numpy as np
import pandas as pd
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import tier1, report


def _session_index(days=150, bars_per_day=26):
    """Grid intraday realist: `days` zile lucratoare x `bars_per_day` bare de 15min
    (09:30->16:00). Resample la '1day' -> `days` bare daily (destule ca indicatorii
    cu fereastra lunga sa se incalzeasca si walk_forward sa aiba istoric)."""
    stamps = []
    for d in pd.bdate_range("2024-01-02", periods=days):
        stamps.extend(pd.date_range(d + pd.Timedelta("9h30m"),
                                    periods=bars_per_day, freq="15min"))
    return pd.DatetimeIndex(stamps)


def _seed(dirpath, symbol):
    idx = _session_index()
    n = len(idx)
    rng = np.random.default_rng(2)
    close = 100 + np.cumsum(rng.normal(0, 0.2, size=n))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_run_validation_produces_report(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    rep = report.run_validation(["AAA", "BBB"], d, tier1.INDICATORS,
                                horizons=(1, 5))
    txt = rep.render_text()
    assert "consiliere de investi" in txt.lower()
    assert "IC" in txt and "ansamblu" in txt.lower()
    assert "hurst" in txt


def test_to_csv_structure(tmp_path):
    import csv
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    rep = report.run_validation(["AAA", "BBB"], d, tier1.INDICATORS,
                                horizons=(1, 5))
    csv_path = tmp_path / "out.csv"
    rep.to_csv(csv_path)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].startswith("#")          # disclaimer ca prima linie
    headers = next(csv.reader(lines[1:]))
    for col in ("indicator", "pooled_ic_h1", "pooled_ic_h5", "marginal_ic_h1"):
        assert col in headers
    body = "\n".join(lines[1:])
    for name in tier1.INDICATORS:
        assert name in body                            # fiecare indicator are rand
