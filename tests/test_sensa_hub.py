import pytest

from markov.data_providers import DataUnavailable
from sensa.hub import Hub


class FakeCboe:
    def __init__(self):
        self.quote_calls = 0

    def quote(self, sym):
        self.quote_calls += 1
        return {"AAA": {"price": 110.0, "prev_close": 100.0},
                "BBB": {"price": 90.0, "prev_close": 100.0}}[sym]

    def chain(self, sym):
        row = lambda t, exp, k: {"option_type": t, "strike": k, "expiration": exp, "gamma": 0.01,
                                 "open_interest": 10, "volume": 4 if t == "call" else 2}
        return 100.0, [row("call", "2026-11-20", 100.0), row("put", "2026-11-20", 100.0),
                       row("call", "2026-10-26", 100.0), row("put", "2026-10-26", 100.0),
                       row("call", "2026-10-26", 500.0)]   # far-OTM strike


class FakeAnalyst:
    def recommendations(self, sym):
        return [{"period": "2026-10-01", "strongBuy": 1, "buy": 1, "hold": 0,
                 "sell": 0, "strongSell": 0}]


def make(now=lambda: 0.0, ttl=60, cboe=None, analyst=FakeAnalyst()):
    return Hub(cboe or FakeCboe(), lambda sym: [{"headline": str(i)} for i in range(30)],
               lambda: {"date": "d", "points": []}, analyst=analyst, ttl=ttl, clock=now,
               today=lambda: "2026-10-26")


def test_movers_for_watchlist_uses_cache_within_ttl():
    cb, t = FakeCboe(), [0.0]
    hub = make(lambda: t[0], 60, cb)
    first = hub.movers(["AAA", "BBB"])
    hub.movers(["AAA", "BBB"])
    assert cb.quote_calls == 2                      # second call served from cache
    assert first["gainers"][0]["symbol"] == "AAA"
    t[0] = 61.0
    hub.movers(["AAA", "BBB"])
    assert cb.quote_calls == 4                      # expired -> refetched


def test_movers_drops_a_symbol_whose_quote_fails_instead_of_failing_all():
    class Flaky(FakeCboe):
        def quote(self, sym):
            if sym == "BBB":
                raise DataUnavailable("nope")
            return super().quote(sym)
    out = make(cboe=Flaky()).movers(["AAA", "BBB"])
    assert [r["symbol"] for r in out["gainers"]] == ["AAA"]


def test_options_uses_nearest_expiration_and_flags_zero_dte():
    o = make().options("aaa")
    assert o["expiration"] == "2026-10-26" and o["zero_dte"] is True
    assert o["cp"]["call_volume"] == 8              # only the nearest expiry counted
    assert o["gex"]["net_gex"] == pytest.approx(1000.0)   # 1000 call + 1000 far call - 1000 put
    assert 500.0 not in [r["strike"] for r in o["gex"]["by_strike"]]   # trimmed to +/-15% of spot


def test_options_none_when_no_chain():
    class Empty(FakeCboe):
        def chain(self, sym):
            return 100.0, []
    assert make(cboe=Empty()).options("AAA") is None


def test_news_is_trimmed_to_limit():
    assert len(make().news(limit=10)) == 10


def test_analyst_is_none_when_not_configured_or_no_data():
    assert make(analyst=None).analyst("AAA") is None
    class Empty(FakeAnalyst):
        def recommendations(self, sym):
            return []
    assert make(analyst=Empty()).analyst("AAA") is None
