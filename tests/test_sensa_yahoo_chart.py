import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.yahoo_chart import YahooChart


def payload(ts, o, h, l, c, v):
    return json.dumps({"chart": {"result": [{"meta": {"symbol": "X"}, "timestamp": ts,
                                             "indicators": {"quote": [{"open": o, "high": h, "low": l, "close": c, "volume": v}]}}],
                       "error": None}})


class Fetch:
    def __init__(self, body):
        self.body, self.urls = body, []

    def __call__(self, url, headers=None):
        self.urls.append(url)
        return self.body


def test_daily_bars_use_date_strings_and_skip_rows_with_missing_prices():
    ts = [1792785600, 1792872000, 1792958400]                       # three sessions
    f = Fetch(payload(ts, [1, None, 3], [2, None, 4], [0.5, None, 2.5], [1.5, None, 3.5], [10, None, 30]))
    bars = YahooChart(f).candles("goog", "1day")
    assert [b["close"] for b in bars] == [1.5, 3.5] and bars[0]["volume"] == 10
    assert isinstance(bars[0]["time"], str) and len(bars[0]["time"]) == 10
    assert "/v8/finance/chart/GOOG?" in f.urls[0] and "interval=1d" in f.urls[0]


def test_intraday_bars_use_unix_seconds_and_the_right_interval():
    f = Fetch(payload([1792785600, 1792789200], [1, 2], [2, 3], [1, 2], [2, 3], [5, 6]))
    bars = YahooChart(f).candles("X", "1h")
    assert bars[0]["time"] == 1792785600 and "interval=60m" in f.urls[0]
    YahooChart(f).candles("X", "15m")
    assert "interval=15m" in f.urls[1]


def test_four_hour_bars_are_built_from_hourly_ones():
    t0 = 20000 * 86400 + 7200                                        # 02:00 UTC: all seven bars fall on one day
    ts = [t0 + 3600 * i for i in range(7)]
    f = Fetch(payload(ts, [1, 2, 3, 4, 5, 6, 7], [10, 11, 12, 13, 14, 15, 16], [0, 1, 2, 3, 4, 5, 6], [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5], [1] * 7))
    bars = YahooChart(f).candles("X", "4h")
    assert len(bars) == 2
    assert (bars[0]["open"], bars[0]["high"], bars[0]["low"], bars[0]["close"], bars[0]["volume"]) == (1, 13, 0, 4.5, 4)
    assert bars[1]["open"] == 5 and bars[1]["volume"] == 3


def test_errors_and_unknown_symbols_become_data_unavailable():
    err = json.dumps({"chart": {"result": None, "error": {"code": "Not Found", "description": "No data found, symbol may be delisted"}}})
    with pytest.raises(DataUnavailable, match="No data"):
        YahooChart(Fetch(err)).candles("ZZZ", "1day")
    with pytest.raises(DataUnavailable):
        YahooChart(Fetch("not json")).candles("X", "1day")
    with pytest.raises(ValueError):
        YahooChart(Fetch("{}")).candles("X", "2d")


def test_symbols_are_validated_before_they_reach_the_url():
    f = Fetch("{}")
    with pytest.raises(ValueError):
        YahooChart(f).candles("A/../B", "1day")
    assert f.urls == []


def test_flat_zero_volume_placeholder_bars_are_dropped_from_intraday_charts():
    f = Fetch(payload([1792785600, 1792789200], [5, 6], [5, 7], [5, 6], [5, 6.5], [0, 100]))
    assert [b["time"] for b in YahooChart(f).candles("X", "1h")] == [1792789200]
