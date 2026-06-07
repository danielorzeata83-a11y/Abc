"""Loader flat files massive: schema standard mapata corect, epoch ns->date,
filtru pe simboluri, eroare clara cand lipseste o coloana."""

import numpy as np
import pandas as pd
import pytest

from markov.massive_loader import load_flat_files, parse_flat_file

# 2020-01-02 si 2020-01-03 in epoch nanosecunde
_NS = {"2020-01-02": 1577923200_000000000, "2020-01-03": 1578009600_000000000}


def _standard_df():
    return pd.DataFrame({
        "ticker": ["AAPL", "AAPL", "MSFT"],
        "volume": [1e6, 1.1e6, 2e6],
        "open": [10.0, 11.0, 20.0], "close": [11.0, 12.0, 21.0],
        "high": [11.5, 12.5, 21.5], "low": [9.5, 10.5, 19.5],
        "window_start": [_NS["2020-01-02"], _NS["2020-01-03"], _NS["2020-01-02"]],
        "transactions": [100, 110, 200],
    })


def test_standard_schema_maps_and_converts_ns():
    out = parse_flat_file(_standard_df())
    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume", "Name"]
    aapl = out[out["Name"] == "AAPL"].sort_values("date")
    assert list(aapl["date"]) == ["2020-01-02", "2020-01-03"]   # ns -> data corecta
    assert aapl.iloc[0]["close"] == 11.0


def test_short_aliases_and_ms_epoch():
    df = pd.DataFrame({"T": ["X"], "o": [1.0], "h": [2.0], "l": [0.5],
                       "c": [1.5], "v": [10], "t": [1577923200_000]})  # ms
    out = parse_flat_file(df)
    assert out.iloc[0]["date"] == "2020-01-02" and out.iloc[0]["high"] == 2.0
    assert out.iloc[0]["Name"] == "X"


def test_missing_column_raises_helpful_error():
    df = pd.DataFrame({"ticker": ["A"], "open": [1.0], "window_start": [_NS["2020-01-02"]]})
    with pytest.raises(ValueError, match="lipsesc coloane"):
        parse_flat_file(df)


def test_load_filters_symbols(tmp_path):
    f = tmp_path / "day.csv"
    _standard_df().to_csv(f, index=False)
    out = load_flat_files([str(f)], symbols=["AAPL"])
    assert set(out["Name"]) == {"AAPL"} and len(out) == 2
