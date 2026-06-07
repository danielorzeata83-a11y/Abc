"""Smoke pentru trendpull_cli: ruleaza pe un CSV long sintetic si verifica
antetul walk-forward, un rand OOS si disclaimerul."""

import numpy as np
import pandas as pd

import trendpull_cli as cli


def _write_csv(path, name="TEST", n=240):
    t = np.arange(n)
    close = 100 + 0.25 * t + 10 * np.sin(t / 6)
    pd.DataFrame({
        "date": pd.bdate_range("2014-01-02", periods=n).astype(str),
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": np.full(n, 1e6), "Name": name,
    }).to_csv(path, index=False)


def test_run_reports_oos_table_and_disclaimer(tmp_path):
    csv = tmp_path / "u.csv"
    _write_csv(csv)
    txt = cli.run(["TEST"], None, str(csv), cost_bps=5.0,
                  mults=(2.0, 3.0), split=0.5, n_perm=50)
    assert "TREND-PULLBACK" in txt and "OOS:" in txt
    assert "TEST" in txt
    assert "consiliere de investi" in txt.lower()
