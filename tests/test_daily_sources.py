"""Surse daily gratis (Stooq / Yahoo / Twelve Data) -> Bars. Offline, opener injectat.

Toate respecta tiparul AV: parsare pura + provider cu opener injectabil. Egress e
blocat in mediul de dezvoltare, deci aici testam doar parsarea + construirea URL-ului.
"""

import json
import numpy as np
import pytest
from urllib.error import URLError

from markov.data_providers import DataUnavailable
from markov.intraday.bars import Bars
from markov.intraday.daily_sources import (
    parse_stooq_csv, StooqDailyProvider,
    parse_yahoo_chart, YahooDailyProvider,
    parse_twelvedata, TwelveDataDailyProvider,
    get_daily_source)


# --- opener fals: pentru CSV (Stooq) si JSON (Yahoo / Twelve Data) ---

def _text_opener(text):
    captured = {}
    def opener(req, timeout=None):
        captured["url"] = req.full_url
        class _R:
            def read(self): return text.encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return _R()
    return opener, captured


def _json_opener(payload):
    return _text_opener(json.dumps(payload))


# --- Stooq (CSV, fara cheie, ascendent) ---

_STOOQ_CSV = ("Date,Open,High,Low,Close,Volume\n"
              "2024-01-02,100.0,101.0,99.0,100.5,4000\n"
              "2024-01-03,101.0,103.0,100.0,102.0,5000\n")


def test_parse_stooq_reads_ohlcv_ascending():
    b = parse_stooq_csv(_STOOQ_CSV)
    assert isinstance(b, Bars) and len(b) == 2
    assert str(b.timestamps[0]).startswith("2024-01-02")
    assert b.open[0] == pytest.approx(100.0)
    assert b.close[-1] == pytest.approx(102.0)
    assert b.volume[1] == pytest.approx(5000.0)


def test_parse_stooq_empty_raises():
    with pytest.raises(DataUnavailable):
        parse_stooq_csv("No data\n")


def test_parse_stooq_rate_limit_message():
    # raspuns non-CSV de rate-limit -> mesaj clar, nu "CSV invalid"
    bodies = ("Exceeded the daily hits limit\n", "<html>blocked</html>",
              "Message\nl2\nl3\nl4\nl5\nl6a,l6b\n")     # tokenizing fail (ca eroarea reala)
    for body in bodies:
        with pytest.raises(DataUnavailable) as ei:
            parse_stooq_csv(body)
        assert "yahoo" in str(ei.value).lower() or "limit" in str(ei.value).lower()


def test_stooq_fetch_builds_us_url_and_returns_bars():
    opener, captured = _text_opener(_STOOQ_CSV)
    b = StooqDailyProvider(opener=opener).fetch("NVDA")
    assert len(b) == 2
    u = captured["url"].lower()
    assert "stooq" in u and "s=nvda.us" in u and "i=d" in u


def test_stooq_network_error_raises():
    def opener(req, timeout=None):
        raise URLError("down")
    with pytest.raises(DataUnavailable):
        StooqDailyProvider(opener=opener).fetch("NVDA")


# --- Yahoo (JSON chart, fara cheie, epoch secunde) ---

def _yahoo_payload():
    return {"chart": {"error": None, "result": [{
        "timestamp": [1704153600, 1704240000],          # 2024-01-02, 2024-01-03
        "indicators": {"quote": [{
            "open": [100.0, 101.0], "high": [101.0, 103.0],
            "low": [99.0, 100.0], "close": [100.5, 102.0],
            "volume": [4000, 5000]}]}}]}}


def test_parse_yahoo_reads_ohlcv():
    b = parse_yahoo_chart(_yahoo_payload())
    assert len(b) == 2
    assert b.open[0] == pytest.approx(100.0)
    assert b.close[-1] == pytest.approx(102.0)


def test_parse_yahoo_skips_null_rows():
    p = _yahoo_payload()
    p["chart"]["result"][0]["indicators"]["quote"][0]["close"] = [100.5, None]
    b = parse_yahoo_chart(p)
    assert len(b) == 1                                   # randul cu null sarit


def test_parse_yahoo_error_raises():
    with pytest.raises(DataUnavailable):
        parse_yahoo_chart({"chart": {"error": "Not Found", "result": None}})


def test_yahoo_fetch_builds_url_and_returns_bars():
    opener, captured = _json_opener(_yahoo_payload())
    b = YahooDailyProvider(opener=opener).fetch("NVDA")
    assert len(b) == 2
    u = captured["url"]
    assert "finance.yahoo.com" in u and "NVDA" in u and "interval=1d" in u


# --- Twelve Data (JSON, cheie, descendent -> sortat ascendent) ---

def _td_payload():
    return {"meta": {"symbol": "NVDA"}, "status": "ok", "values": [
        {"datetime": "2024-01-03", "open": "101.0", "high": "103.0",
         "low": "100.0", "close": "102.0", "volume": "5000"},
        {"datetime": "2024-01-02", "open": "100.0", "high": "101.0",
         "low": "99.0", "close": "100.5", "volume": "4000"}]}


def test_parse_twelvedata_sorts_ascending():
    b = parse_twelvedata(_td_payload())
    assert len(b) == 2
    assert str(b.timestamps[0]).startswith("2024-01-02")
    assert b.close[-1] == pytest.approx(102.0)


def test_parse_twelvedata_error_raises():
    with pytest.raises(DataUnavailable):
        parse_twelvedata({"status": "error", "message": "limit"})


def test_twelvedata_fetch_builds_url_with_key():
    opener, captured = _json_opener(_td_payload())
    b = TwelveDataDailyProvider("KEY123", opener=opener).fetch("NVDA")
    assert len(b) == 2
    u = captured["url"]
    for token in ("twelvedata.com", "symbol=NVDA", "interval=1day", "KEY123"):
        assert token in u


# --- dispatch unic ---

def test_get_daily_source_dispatch():
    assert isinstance(get_daily_source("stooq"), StooqDailyProvider)
    assert isinstance(get_daily_source("yahoo"), YahooDailyProvider)
    assert isinstance(get_daily_source("td:KEY"), TwelveDataDailyProvider)
    with pytest.raises(ValueError):
        get_daily_source("nope:x")
