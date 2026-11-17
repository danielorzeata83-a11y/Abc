"""Smoke pentru dipbuy_cli: ruleaza pe un CSV long sintetic (cu o cadere) si
verifica antetul, randul SISTEM/B&H, linia POOLED si disclaimerul."""

import numpy as np
import pandas as pd

import dipbuy_cli as cli


def _write_csv(path, name="TEST"):
    up = np.linspace(50, 100, 120)
    crash = np.linspace(100, 62, 30)
    rec = np.linspace(62, 110, 120)
    close = np.concatenate([up, crash, rec])
    pd.DataFrame({
        "date": pd.bdate_range("2014-01-02", periods=len(close)).astype(str),
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": np.full(len(close), 1e6), "Name": name,
    }).to_csv(path, index=False)


def test_run_reports_table_pooled_and_disclaimer(tmp_path):
    csv = tmp_path / "u.csv"
    _write_csv(csv)
    txt = cli.run(["TEST"], None, str(csv), cost_bps=5.0, dips=[0.1, 0.2],
                  split=0.5, lookback=60, exit_ma=20, n_perm=50)
    assert "BUY-THE-DIP" in txt and "B&H" in txt and "POOLED" in txt
    assert "TEST" in txt
    assert "consiliere de investi" in txt.lower()
