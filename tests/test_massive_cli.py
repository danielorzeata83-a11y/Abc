"""Smoke massive_cli: flat file -> CSV lung in formatul sp500, gata de dashboard."""

import pandas as pd

import massive_cli as cli

_NS = 1577923200_000000000   # 2020-01-02


def test_converts_flat_file_to_long_csv(tmp_path):
    src = tmp_path / "day.csv"
    pd.DataFrame({"ticker": ["NVDA", "AAPL"], "volume": [1e6, 2e6],
                  "open": [5.0, 10.0], "close": [6.0, 11.0], "high": [6.5, 11.5],
                  "low": [4.5, 9.5], "window_start": [_NS, _NS],
                  "transactions": [10, 20]}).to_csv(src, index=False)
    out = tmp_path / "long.csv"
    rc = cli.main(["--in", str(src), "--symbols", "NVDA", "--out", str(out)])
    assert rc == 0
    d = pd.read_csv(out)
    assert list(d.columns) == ["date", "open", "high", "low", "close", "volume", "Name"]
    assert set(d["Name"]) == {"NVDA"} and d.iloc[0]["date"] == "2020-01-02"
