"""Tests for the pluggable fundamentals-provider layer."""

import pandas as pd
import pytest
from markov.fundamentals_provider import (
    get_fundamentals_provider, CSVFundamentalsProvider, FMPProvider, FUND_COLUMNS,
)
from markov.data_providers import DataUnavailable


@pytest.fixture
def tiny_csv(tmp_path):
    df = pd.DataFrame({
        "Symbol": ["AAA", "BBB"], "Name": ["A", "B"], "Sector": ["Tech", "Energy"],
        "Price": [10, 20], "Price/Earnings": [8.0, 25.0], "Dividend Yield": [0.03, 0.01],
        "Earnings/Share": [1.2, 0.8], "52 Week Low": [5, 10], "52 Week High": [12, 22],
        "Market Cap": [1e9, 2e9], "EBITDA": [4e8, 5e8],
        "Price/Sales": [1.0, 2.0], "Price/Book": [1.0, 3.0],
        "SEC Filings": ["x", "y"],
    })
    p = tmp_path / "fin.csv"
    df.to_csv(p, index=False)
    return str(p)


def test_csv_provider_returns_expected_columns(tiny_csv):
    df = CSVFundamentalsProvider(tiny_csv).fetch()
    for c in FUND_COLUMNS:
        assert c in df.columns
    assert len(df) == 2


def test_csv_provider_filters_tickers(tiny_csv):
    df = CSVFundamentalsProvider(tiny_csv).fetch(["AAA"])
    assert list(df["Symbol"]) == ["AAA"]


def test_csv_provider_unknown_ticker_raises(tiny_csv):
    with pytest.raises(KeyError):
        CSVFundamentalsProvider(tiny_csv).fetch(["ZZZ"])


def test_get_provider_csv(tiny_csv):
    assert isinstance(get_fundamentals_provider(f"csv:{tiny_csv}"),
                      CSVFundamentalsProvider)


def test_get_provider_fmp_needs_key():
    assert isinstance(get_fundamentals_provider("fmp:DEMOKEY"), FMPProvider)


def test_fmp_offline_raises():
    prov = get_fundamentals_provider("fmp:DEMOKEY")
    with pytest.raises(DataUnavailable):
        prov.fetch(["AAPL"])
