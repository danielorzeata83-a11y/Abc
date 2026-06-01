"""Tests for the OHLCV/price data loader.

The loader reads a CSV with at least a date column and a price column,
drops rows with missing prices, returns data sorted by date, and exposes
a clean numpy price array for the rest of the engine.
"""

import numpy as np
import pytest

from markov.data import load_prices


def _write_csv(tmp_path, text):
    p = tmp_path / "prices.csv"
    p.write_text(text)
    return str(p)


def test_loads_date_and_price_columns(tmp_path):
    csv = _write_csv(tmp_path, "time,PriceUSD\n2020-01-01,100\n2020-01-02,110\n")
    df = load_prices(csv, date_col="time", price_col="PriceUSD")
    assert list(df["price"]) == [100.0, 110.0]
    assert len(df) == 2


def test_drops_rows_with_missing_price(tmp_path):
    csv = _write_csv(
        tmp_path,
        "time,PriceUSD\n2009-01-03,\n2009-01-04,\n2020-01-01,100\n2020-01-02,110\n",
    )
    df = load_prices(csv, date_col="time", price_col="PriceUSD")
    assert len(df) == 2
    assert df["price"].iloc[0] == 100.0


def test_sorted_by_date_ascending(tmp_path):
    csv = _write_csv(
        tmp_path,
        "time,PriceUSD\n2020-01-03,103\n2020-01-01,101\n2020-01-02,102\n",
    )
    df = load_prices(csv, date_col="time", price_col="PriceUSD")
    assert list(df["price"]) == [101.0, 102.0, 103.0]


def test_price_array_helper_returns_float_ndarray(tmp_path):
    csv = _write_csv(tmp_path, "time,PriceUSD\n2020-01-01,100\n2020-01-02,110\n")
    df = load_prices(csv, date_col="time", price_col="PriceUSD")
    arr = df["price"].to_numpy()
    assert arr.dtype == np.float64
    assert arr.tolist() == [100.0, 110.0]


def test_rejects_missing_columns(tmp_path):
    csv = _write_csv(tmp_path, "date,close\n2020-01-01,100\n")
    with pytest.raises((KeyError, ValueError)):
        load_prices(csv, date_col="time", price_col="PriceUSD")


def test_drops_zero_and_negative_prices(tmp_path):
    csv = _write_csv(
        tmp_path,
        "time,PriceUSD\n2020-01-01,0\n2020-01-02,-5\n2020-01-03,100\n",
    )
    df = load_prices(csv, date_col="time", price_col="PriceUSD")
    assert list(df["price"]) == [100.0]
