"""Tests for the pluggable data-provider layer.

A provider returns a PanelData(prices, volume, dates, tickers) for a list
of tickers. CSVPanelProvider reads the bundled long-format CSV; live
providers (Stooq/Yahoo) are implemented but only work when the host is
allowlisted -- offline they raise a clear DataUnavailable.
"""

import numpy as np
import pandas as pd
import pytest

from markov.data_providers import (
    PanelData, CSVPanelProvider, get_provider, DataUnavailable,
)


@pytest.fixture
def tiny_csv(tmp_path):
    rows = []
    for tic in ["AAA", "BBB", "CCC"]:
        for i, d in enumerate(pd.bdate_range("2020-01-01", periods=10)):
            rows.append({"date": d.date(), "open": 10 + i, "high": 11 + i,
                         "low": 9 + i, "close": 10 + i + (tic == "BBB"),
                         "volume": 1000 * (i + 1), "Name": tic})
    p = tmp_path / "panel.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return str(p)


def test_csv_provider_returns_paneldata(tiny_csv):
    pd_ = CSVPanelProvider(tiny_csv).fetch(["AAA", "BBB"])
    assert isinstance(pd_, PanelData)
    assert pd_.tickers == ["AAA", "BBB"]
    assert pd_.prices.shape == (10, 2)
    assert pd_.volume.shape == (10, 2)
    assert len(pd_.dates) == 10


def test_csv_provider_all_tickers_when_none(tiny_csv):
    pd_ = CSVPanelProvider(tiny_csv).fetch(None)
    assert set(pd_.tickers) == {"AAA", "BBB", "CCC"}


def test_csv_provider_unknown_ticker_raises(tiny_csv):
    with pytest.raises(KeyError):
        CSVPanelProvider(tiny_csv).fetch(["ZZZ"])


def test_get_provider_csv(tiny_csv):
    prov = get_provider(f"csv:{tiny_csv}")
    assert isinstance(prov, CSVPanelProvider)


def test_live_provider_offline_raises_clear_error():
    prov = get_provider("stooq")
    with pytest.raises(DataUnavailable):
        prov.fetch(["NVDA"])


def test_coinmetrics_parse_extracts_price_and_volume():
    from markov.data_providers import parse_coinmetrics_csv
    df = pd.DataFrame({
        "time": ["2021-01-01", "2021-01-02", "2021-01-03"],
        "PriceUSD": [100.0, 110.0, np.nan],
        "VolTrustedSpotUSD": [5.0, 6.0, 7.0],
    })
    close, vol = parse_coinmetrics_csv(df)
    # Row with NaN price is dropped.
    assert list(close.values) == [100.0, 110.0]
    assert list(vol.values) == [5.0, 6.0]
    assert close.name == "close" and vol.name == "volume"


def test_coinmetrics_parse_missing_volume_returns_nan():
    from markov.data_providers import parse_coinmetrics_csv
    df = pd.DataFrame({"time": ["2021-01-01"], "PriceUSD": [100.0]})
    close, vol = parse_coinmetrics_csv(df)
    assert close.iloc[0] == 100.0
    assert np.isnan(vol.iloc[0])


def test_get_provider_coinmetrics():
    from markov.data_providers import CoinMetricsProvider
    assert isinstance(get_provider("coinmetrics"), CoinMetricsProvider)
