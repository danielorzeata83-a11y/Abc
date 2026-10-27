import json

import numpy as np
import pandas as pd
import pytest

from markov.data_providers import DataUnavailable
from sensa.lab_data import load_prices, to_returns
from sensa.yahoo_chart import YahooChart


def payload(ts, close, adj):
    return json.dumps({"chart": {"result": [{"meta": {"gmtoffset": 0}, "timestamp": ts,
                                             "indicators": {"quote": [{"open": close, "high": close, "low": close, "close": close, "volume": [1] * len(ts)}],
                                                            "adjclose": [{"adjclose": adj}]}}], "error": None}})


def test_adjusted_closes_include_dividends_and_skip_missing_rows():
    ts = [20000 * 86400 + i * 86400 for i in range(4)]
    f = lambda url, headers=None: payload(ts, [10, 10, None, 11], [9.0, 9.5, None, 11.0])
    rows = YahooChart(f).adjusted("x", years=10)
    assert [r[1] for r in rows] == [9.0, 9.5, 11.0] and len(rows[0][0]) == 10


def test_adjusted_requests_the_requested_range_and_rejects_bad_symbols():
    seen = []
    f = lambda url, headers=None: (seen.append(url), payload([20000 * 86400], [1], [1]))[1]
    YahooChart(f).adjusted("AAPL", years=3)
    assert "range=3y" in seen[0] and "interval=1d" in seen[0]
    with pytest.raises(ValueError):
        YahooChart(f).adjusted("A/B", years=3)


def hist(series):
    def fn(sym):
        if sym not in series:
            raise DataUnavailable("no data")
        return series[sym]
    return fn


def days(n, start=20000):
    return [pd.Timestamp(start * 86400 + i * 86400, unit="s").strftime("%Y-%m-%d") for i in range(n)]


def test_load_prices_aligns_on_common_dates_reports_dropped_tickers_and_hashes_the_data():
    d = days(300)
    series = {"A": list(zip(d, np.linspace(10, 20, 300))), "B": list(zip(d[10:], np.linspace(5, 6, 290))),       # B starts later
              "C": list(zip(d[:50], np.linspace(1, 2, 50)))}                                                    # C too short
    prices, manifest = load_prices(["A", "B", "C", "ZZZ"], hist(series), min_rows=200)
    assert list(prices.columns) == ["A", "B"] and len(prices) == 290 and prices.index[0] == d[10]
    assert manifest["tickers"] == ["A", "B"] and manifest["rows"] == 290 and manifest["start"] == d[10] and manifest["end"] == d[-1]
    assert {x["ticker"] for x in manifest["dropped"]} == {"C", "ZZZ"} and len(manifest["sha256"]) == 64
    again, m2 = load_prices(["A", "B", "C", "ZZZ"], hist(series), min_rows=200)
    assert m2["sha256"] == manifest["sha256"]


def test_returns_are_simple_daily_returns_and_implausible_jumps_are_flagged_not_hidden():
    idx = pd.Index(days(5))
    p = pd.DataFrame({"A": [100.0, 110.0, 99.0, 300.0, 303.0]}, index=idx)
    r, flagged = to_returns(p, jump=0.5)
    assert r["A"].iloc[0] == pytest.approx(0.10) and len(r) == 4
    assert [(f["ticker"], f["date"]) for f in flagged] == [("A", idx[3])]


def test_fewer_than_two_usable_tickers_is_an_error():
    d = days(300)
    with pytest.raises(DataUnavailable, match="at least two"):
        load_prices(["A"], hist({"A": list(zip(d, np.linspace(1, 2, 300)))}), min_rows=200)
