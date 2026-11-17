"""Smoke pentru trade_report_cli: tabel de trader + linia POOLED + disclaimer,
pentru ambele sisteme."""

import numpy as np
import pandas as pd
import pytest

import trade_report_cli as cli


def _write_csv(path, name="TEST"):
    t = np.arange(260)
    close = 100 + 0.2 * t + 10 * np.sin(t / 6)
    pd.DataFrame({
        "date": pd.bdate_range("2014-01-02", periods=len(close)).astype(str),
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": np.full(len(close), 1e6), "Name": name,
    }).to_csv(path, index=False)


@pytest.mark.parametrize("system", ["trend", "dip"])
def test_run_reports_trader_table(tmp_path, system):
    csv = tmp_path / "u.csv"
    _write_csv(csv)
    txt = cli.run(system, ["TEST"], None, str(csv), cost_bps=5.0,
                  split=0.5, n_perm=50)
    assert f"sistem '{system}'" in txt
    assert "win%" in txt and "PF" in txt
    assert "consiliere de investi" in txt.lower()
