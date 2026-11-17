"""Smoke pentru dip_dashboard_cli: scrie un HTML self-contained cu numele si
disclaimerul."""

import numpy as np
import pandas as pd

import dip_dashboard_cli as cli


def _universe(tmp_path):
    csv = tmp_path / "u.csv"
    fall = np.concatenate([np.linspace(50, 100, 80), np.linspace(100, 55, 20)])
    rows = []
    for d, c in zip(pd.bdate_range("2015-01-02", periods=len(fall)).astype(str), fall):
        rows.append({"date": d, "open": c, "high": c, "low": c, "close": c,
                     "volume": 1e6, "Name": "FALL"})
    pd.DataFrame(rows).to_csv(csv, index=False)
    return str(csv)


def test_writes_self_contained_html(tmp_path):
    out = tmp_path / "dip.html"
    rc = cli.main(["--watchlist", "FALL", "--universe", _universe(tmp_path),
                   "--dip", "0.4", "--out", str(out)])
    assert rc == 0
    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html and "FALL" in html
    assert "consiliere de investi" in html.lower()
    assert "http://" not in html and "https://" not in html
