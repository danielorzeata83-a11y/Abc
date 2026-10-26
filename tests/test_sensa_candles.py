import numpy as np
import pytest

from markov.data_providers import DataUnavailable
from markov.intraday.bars import Bars
from sensa.candles import make_candles_fn


def daily_bars():
    ts = np.array(["2026-10-22", "2026-10-23"], dtype="datetime64[ns]")
    return Bars(ts, np.array([1.0, 2.0]), np.array([3.0, 4.0]), np.array([0.5, 1.5]),
                np.array([2.0, 3.0]), np.array([100.0, 200.0]))


class FakeDaily:
    def __init__(self):
        self.calls = []

    def fetch(self, symbol):
        self.calls.append(symbol)
        return daily_bars()


def no_cache(sym, tf, data_dir):
    raise DataUnavailable(f"No cached data for {sym}")


def test_intraday_cache_is_preferred_when_present():
    fn = make_candles_fn("d", daily=FakeDaily(), intraday=lambda s, tf, d: [{"time": 1, "src": "cache"}])
    assert fn("AAPL", "1h") == [{"time": 1, "src": "cache"}]


def test_falls_back_to_daily_provider_only_for_1day_and_converts_bars():
    d = FakeDaily()
    out = make_candles_fn("d", daily=d, intraday=no_cache)("aapl", "1day")
    assert d.calls == ["AAPL"]
    assert out[1] == {"time": "2026-10-23", "open": 2.0, "high": 4.0, "low": 1.5,
                      "close": 3.0, "volume": 200.0}


def test_intraday_timeframes_without_cache_explain_the_premium_limit():
    with pytest.raises(DataUnavailable, match="premium"):
        make_candles_fn("d", daily=FakeDaily(), intraday=no_cache)("AAPL", "1h")


def test_without_daily_provider_the_message_says_to_set_the_key():
    with pytest.raises(DataUnavailable, match="ALPHAVANTAGE_API_KEY"):
        make_candles_fn("d", daily=None, intraday=no_cache)("AAPL", "1day")


def test_provider_errors_never_leak_the_api_key():
    class Leaky:
        def fetch(self, symbol):
            raise DataUnavailable("failed https://x/query?apikey=SECRETKEY&symbol=AAPL")
    with pytest.raises(DataUnavailable) as e:
        make_candles_fn("d", daily=Leaky(), intraday=no_cache, secret="SECRETKEY")("AAPL", "1day")
    assert "SECRETKEY" not in str(e.value)


class FakeYahoo:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def candles(self, symbol, tf):
        self.calls.append((symbol, tf))
        if self.fail:
            raise DataUnavailable("yahoo down")
        return [{"time": 1, "src": "yahoo"}]


def test_yahoo_serves_every_timeframe_when_there_is_no_local_cache_and_spares_the_alpha_vantage_quota():
    d, y = FakeDaily(), FakeYahoo()
    fn = make_candles_fn("d", daily=d, intraday=no_cache, yahoo=y)
    assert fn("aapl", "1h") == [{"time": 1, "src": "yahoo"}] and fn("AAPL", "1day") == [{"time": 1, "src": "yahoo"}]
    assert d.calls == [] and y.calls == [("AAPL", "1h"), ("AAPL", "1day")]


def test_the_local_cache_still_wins_over_yahoo():
    y = FakeYahoo()
    fn = make_candles_fn("d", intraday=lambda s, tf, d: [{"time": 9, "src": "cache"}], yahoo=y)
    assert fn("AAPL", "1h")[0]["src"] == "cache" and y.calls == []


def test_when_yahoo_fails_daily_falls_back_to_alpha_vantage_and_intraday_reports_the_yahoo_error():
    d = FakeDaily()
    fn = make_candles_fn("d", daily=d, intraday=no_cache, yahoo=FakeYahoo(fail=True))
    assert fn("AAPL", "1day")[1]["close"] == 3.0 and d.calls == ["AAPL"]
    with pytest.raises(DataUnavailable, match="yahoo down"):
        fn("AAPL", "1h")
