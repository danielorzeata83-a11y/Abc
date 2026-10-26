import pytest

from markov.data_providers import DataUnavailable
from sensa.prices import PriceBook

BARS = [{"time": "2026-06-29", "close": 10.0}, {"time": "2026-06-30", "close": 11.0},
        {"time": "2026-07-02", "close": 12.0}, {"time": "2026-07-03", "close": 13.0}]


class Hist:
    def __init__(self):
        self.calls = []

    def __call__(self, t):
        self.calls.append(t)
        if t == "NOPE":
            raise DataUnavailable("no data")
        return BARS


def test_close_on_or_before_and_after_use_the_nearest_trading_day():
    pb = PriceBook(Hist())
    assert pb.on_or_before("X", "2026-07-01") == (("2026-06-30"), 11.0)
    assert pb.on_or_after("X", "2026-07-01") == ("2026-07-02", 12.0)
    assert pb.on_or_before("X", "2026-06-30") == ("2026-06-30", 11.0)
    assert pb.on_or_before("X", "2026-06-01") is None and pb.on_or_after("X", "2026-08-01") is None


def test_last_close_and_one_download_per_ticker():
    h = Hist()
    pb = PriceBook(h)
    assert pb.last("x") == ("2026-07-03", 13.0)
    pb.on_or_before("X", "2026-07-01")
    assert h.calls == ["X"]


def test_unknown_tickers_give_none_and_are_not_retried_within_the_ttl():
    h, t = Hist(), [0.0]
    pb = PriceBook(h, clock=lambda: t[0], ttl=3600)
    assert pb.last("NOPE") is None and pb.on_or_after("NOPE", "2026-07-01") is None
    assert h.calls == ["NOPE"]
    t[0] = 4000
    pb.last("NOPE")
    assert h.calls == ["NOPE", "NOPE"]


def test_warm_loads_many_tickers_in_parallel_and_survives_failures():
    h = Hist()
    pb = PriceBook(h, workers=4)
    pb.warm(["A", "B", "NOPE", "C"])
    assert sorted(h.calls) == ["A", "B", "C", "NOPE"] and pb.last("B") == ("2026-07-03", 13.0)


def test_prices_persist_on_disk_between_runs(tmp_path):
    path = str(tmp_path / "prices.json")
    first = PriceBook(Hist(), cache_path=path)
    first.last("X")
    first.save()
    boom = lambda t: (_ for _ in ()).throw(AssertionError("network"))
    assert PriceBook(boom, cache_path=path).last("X") == ("2026-07-03", 13.0)
