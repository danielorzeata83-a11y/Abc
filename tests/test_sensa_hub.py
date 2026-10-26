import pytest

from markov.data_providers import DataUnavailable
from sensa.hub import Hub


class FakeFinnhub:
    def __init__(self):
        self.quote_calls = 0

    def quote(self, sym):
        self.quote_calls += 1
        return {"AAA": {"price": 110.0, "prev_close": 100.0},
                "BBB": {"price": 90.0, "prev_close": 100.0}}[sym]

    def recommendations(self, sym):
        return [{"period": "2026-10-01", "strongBuy": 1, "buy": 1, "hold": 0,
                 "sell": 0, "strongSell": 0}]

    def news(self, sym=None):
        return [{"headline": "h", "url": "u", "source": "s", "datetime": 1}] * 30


class FakeTradier:
    def expirations(self, sym):
        return ["2026-11-20", "2026-12-18"]

    def chain(self, sym, exp):
        return [{"option_type": "call", "strike": 100.0, "volume": 4, "open_interest": 8},
                {"option_type": "put", "strike": 100.0, "volume": 2, "open_interest": 4}]


def make(now=lambda: 0.0, ttl=60, fh=None):
    return Hub(fh or FakeFinnhub(), FakeTradier(), lambda: "x", ttl=ttl, clock=now)


def test_movers_for_watchlist_uses_cache_within_ttl():
    fh, t = FakeFinnhub(), [0.0]
    hub = make(lambda: t[0], 60, fh)
    first = hub.movers(["AAA", "BBB"])
    hub.movers(["AAA", "BBB"])
    assert fh.quote_calls == 2                      # second call served from cache
    assert first["gainers"][0]["symbol"] == "AAA"
    t[0] = 61.0
    hub.movers(["AAA", "BBB"])
    assert fh.quote_calls == 4                      # expired -> refetched


def test_movers_drops_a_symbol_whose_quote_fails_instead_of_failing_all():
    class Flaky(FakeFinnhub):
        def quote(self, sym):
            if sym == "BBB":
                raise DataUnavailable("nope")
            return super().quote(sym)
    out = make(fh=Flaky()).movers(["AAA", "BBB"])
    assert [r["symbol"] for r in out["gainers"]] == ["AAA"]


def test_options_snapshot_uses_nearest_expiration_and_computes_ratio():
    o = make().options("aaa")
    assert o["expiration"] == "2026-11-20"
    assert o["cp"]["volume_ratio"] == 2.0
    assert len(o["chain"]) == 2


def test_news_is_trimmed_to_limit():
    assert len(make().news(limit=10)) == 10


def test_analyst_returns_none_when_no_data():
    class Empty(FakeFinnhub):
        def recommendations(self, sym):
            return []
    assert make(fh=Empty()).analyst("AAA") is None
