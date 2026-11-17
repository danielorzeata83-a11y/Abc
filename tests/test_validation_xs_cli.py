"""Smoke TIER 2b CLI: ruleaza pe un univers sintetic si tipareste raportul."""

import numpy as np
import pandas as pd

import validate_xs_cli


def _panel_csv(tmp_path, T=200, N=10, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=T)
    rows = []
    for j in range(N):
        close = 100 * np.cumprod(1 + rng.normal(0, 0.02, T))
        vol = rng.uniform(1e5, 1e6, T)
        for i, d in enumerate(dates):
            c = close[i]
            rows.append((d.strftime("%Y-%m-%d"), c, c, c, c, vol[i], f"S{j:02d}"))
    p = tmp_path / "uni.csv"
    pd.DataFrame(rows, columns=["date", "open", "high", "low", "close",
                                "volume", "Name"]).to_csv(p, index=False)
    return str(p)


def test_cli_runs_and_prints_report(tmp_path, capsys):
    csv = _panel_csv(tmp_path)
    validate_xs_cli.main(["--universe", csv, "--n-perm", "200"])
    out = capsys.readouterr().out
    assert "TIER 2b" in out and "Sharpe_OOS" in out
    assert "consiliere de investi" in out.lower()
    assert "momentum" in out and "amihud" in out
