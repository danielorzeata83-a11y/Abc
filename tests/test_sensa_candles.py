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


def test_without_daily_provider_the_cache_error_propagates():
    with pytest.raises(DataUnavailable, match="No cached data"):
        make_candles_fn("d", daily=None, intraday=no_cache)("AAPL", "1day")


def test_provider_errors_never_leak_the_api_key():
    class Leaky:
        def fetch(self, symbol):
            raise DataUnavailable("failed https://x/query?apikey=SECRETKEY&symbol=AAPL")
    with pytest.raises(DataUnavailable) as e:
        make_candles_fn("d", daily=Leaky(), intraday=no_cache, secret="SECRETKEY")("AAPL", "1day")
    assert "SECRETKEY" not in str(e.value)
