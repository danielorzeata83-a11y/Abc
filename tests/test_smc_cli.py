"""Smoke pentru smc_backtest_cli: ruleaza pe un CSV long sintetic si verifica
ca raportul contine antetul, sweep-ul de cost si disclaimerul."""

import numpy as np
import pandas as pd

import smc_backtest_cli as cli


def _write_csv(path):
    n = 120
    close = 100 * np.cumprod(1 + np.sin(np.arange(n) / 5) * 0.01 + 0.001)
    pd.DataFrame({
        "date": pd.bdate_range("2015-01-02", periods=n).astype(str),
        "open": close, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": np.full(n, 1e6), "Name": "TEST",
    }).to_csv(path, index=False)


def test_run_reports_header_costs_and_disclaimer(tmp_path):
    csv = tmp_path / "u.csv"
    _write_csv(csv)
    txt = cli.run("TEST", None, str(csv), costs_bps=[0.0, 10.0],
                  k=2, timeout=10, ppy=252, n_perm=50)
    assert "SMC (BOS + retest FVG) pe TEST" in txt
    assert "cost= 0.0 bps" in txt and "cost=10.0 bps" in txt
    assert "consiliere de investi" in txt.lower()
