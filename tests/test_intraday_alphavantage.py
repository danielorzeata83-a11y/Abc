"""Alpha Vantage intraday provider (offline, fixture + injected opener)."""

import io
import json
import numpy as np
import pytest
from urllib.error import URLError

from markov.data_providers import DataUnavailable
from markov.intraday.bars import Bars
from markov.intraday.alphavantage import (
    parse_av_intraday, AlphaVantageIntradayProvider, get_intraday_provider,
    parse_av_daily, AlphaVantageDailyProvider, get_daily_provider)


def _payload():
    return {"Meta Data": {"2. Symbol": "NVDA"},
            "Time Series (15min)": {
                "2025-07-03 15:45:00": {"1. open": "100.0", "2. high": "101.0",
                    "3. low": "99.0", "4. close": "100.5", "5. volume": "1000"},
                "2025-07-03 15:30:00": {"1. open": "99.0", "2. high": "100.0",
                    "3. low": "98.0", "4. close": "99.5", "5. volume": "800"}}}


def test_parse_sorts_ascending_and_reads_ohlcv():
    b = parse_av_intraday(_payload())
    assert isinstance(b, Bars)
    assert len(b) == 2
    assert str(b.timestamps[0]).startswith("2025-07-03T15:30")   # sorted asc
    assert b.open[0] == pytest.approx(99.0)
    assert b.close[-1] == pytest.approx(100.5)
    assert b.volume[0] == pytest.approx(800.0)


@pytest.mark.parametrize("bad", [{"Note": "5 calls/min"}, {"Information": "premium"},
                                 {"Error Message": "bad symbol"}])
def test_throttle_or_error_raises(bad):
    with pytest.raises(DataUnavailable):
        parse_av_intraday(bad)


def _fake_opener(payload):
    captured = {}
    def opener(req, timeout=None):
        captured["url"] = req.full_url
        class _R:
            def read(self): return json.dumps(payload).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return _R()
    return opener, captured


def test_fetch_month_builds_url_and_returns_bars():
    opener, captured = _fake_opener(_payload())
    prov = AlphaVantageIntradayProvider("KEY123", opener=opener)
    b = prov.fetch_month("NVDA", "2025-07")
    assert len(b) == 2
    u = captured["url"]
    for token in ("function=TIME_SERIES_INTRADAY", "interval=15min",
                  "month=2025-07", "outputsize=full", "KEY123", "symbol=NVDA"):
        assert token in u


def test_fetch_month_network_error_raises():
    def opener(req, timeout=None):
        raise URLError("down")
    prov = AlphaVantageIntradayProvider("K", opener=opener)
    with pytest.raises(DataUnavailable):
        prov.fetch_month("NVDA", "2025-07")


def test_get_provider_spec():
    assert isinstance(get_intraday_provider("av:KEY"), AlphaVantageIntradayProvider)
    with pytest.raises(ValueError):
        get_intraday_provider("nope:x")


# --- daily (free tier: TIME_SERIES_DAILY, full history, 1 call/simbol) ---

def _daily_payload():
    return {"Meta Data": {"2. Symbol": "NVDA"},
            "Time Series (Daily)": {
                "2024-01-03": {"1. open": "101.0", "2. high": "103.0",
                    "3. low": "100.0", "4. close": "102.0", "5. volume": "5000"},
                "2024-01-02": {"1. open": "100.0", "2. high": "101.0",
                    "3. low": "99.0", "4. close": "100.5", "5. volume": "4000"}}}


def test_parse_daily_sorts_ascending_and_reads_ohlcv():
    b = parse_av_daily(_daily_payload())
    assert isinstance(b, Bars)
    assert len(b) == 2
    assert str(b.timestamps[0]).startswith("2024-01-02")          # sorted asc
    assert b.open[0] == pytest.approx(100.0)
    assert b.close[-1] == pytest.approx(102.0)
    assert b.volume[0] == pytest.approx(4000.0)


@pytest.mark.parametrize("bad", [{"Note": "5 calls/min"}, {"Information": "premium"},
                                 {"Error Message": "bad symbol"}])
def test_parse_daily_throttle_or_error_raises(bad):
    with pytest.raises(DataUnavailable):
        parse_av_daily(bad)


def test_fetch_daily_builds_url_and_returns_bars():
    opener, captured = _fake_opener(_daily_payload())
    prov = AlphaVantageDailyProvider("KEY123", opener=opener)
    b = prov.fetch("NVDA")
    assert len(b) == 2
    u = captured["url"]
    for token in ("function=TIME_SERIES_DAILY", "outputsize=full",
                  "KEY123", "symbol=NVDA"):
        assert token in u


def test_fetch_daily_network_error_raises():
    def opener(req, timeout=None):
        raise URLError("down")
    prov = AlphaVantageDailyProvider("K", opener=opener)
    with pytest.raises(DataUnavailable):
        prov.fetch("NVDA")


def test_get_daily_provider_spec():
    assert isinstance(get_daily_provider("av:KEY"), AlphaVantageDailyProvider)
    with pytest.raises(ValueError):
        get_daily_provider("nope:x")
