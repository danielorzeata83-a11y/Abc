import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.providers import Cboe, Finnhub, FredApi, yahoo_news


class FakeFetch:
    def __init__(self, body):
        self.body, self.calls = body, []

    def __call__(self, url, headers=None):
        self.calls.append((url, headers or {}))
        return self.body if isinstance(self.body, str) else json.dumps(self.body)


QUOTE = {"data": {"symbol": "AAPL", "current_price": 347.61, "prev_day_close": 347.73,
                  "price_change_percent": -0.1424, "iv30": 26.5}}


def test_cboe_quote_maps_fields_and_uppercases():
    f = FakeFetch(QUOTE)
    q = Cboe(fetch=f).quote("aapl")
    assert q == {"price": 347.61, "prev_close": 347.73, "iv30": 26.5}
    assert f.calls[0][0].endswith("/delayed_quotes/quotes/AAPL.json")


def test_cboe_index_symbols_get_underscore_prefix():
    f = FakeFetch(QUOTE)
    Cboe(fetch=f).quote("spx")
    assert f.calls[0][0].endswith("/delayed_quotes/quotes/_SPX.json")


def test_cboe_chain_parses_occ_symbols_and_returns_spot():
    body = {"data": {"current_price": 100.0, "options": [
        {"option": "AAPL261120C00245000", "gamma": 0.01, "delta": 0.5, "iv": 0.3,
         "open_interest": 7, "volume": 3, "bid": 1.0, "ask": 1.2},
        {"option": "AAPL261026P00090500", "gamma": 0.02, "delta": -0.2, "iv": 0.4,
         "open_interest": 5, "volume": 1, "bid": 0.1, "ask": 0.2}]}}
    spot, chain = Cboe(fetch=FakeFetch(body)).chain("aapl")
    assert spot == 100.0
    assert chain[0] == {"option_type": "call", "strike": 245.0, "expiration": "2026-11-20",
                        "gamma": 0.01, "delta": 0.5, "iv": 0.3, "open_interest": 7,
                        "volume": 3, "bid": 1.0, "ask": 1.2}
    assert chain[1]["option_type"] == "put" and chain[1]["strike"] == 90.5
    assert chain[1]["expiration"] == "2026-10-26"


def test_cboe_chain_skips_unparseable_symbols():
    body = {"data": {"current_price": 1.0, "options": [{"option": "garbage"}]}}
    assert Cboe(fetch=FakeFetch(body)).chain("X") == (1.0, [])


class FredFetch:
    """Serves FRED observations per series id (newest first, like sort_order=desc)."""
    def __init__(self, data):
        self.data, self.calls = data, []

    def __call__(self, url, headers=None):
        self.calls.append(url)
        sid = url.split("series_id=")[1].split("&")[0]
        return json.dumps({"observations": [{"date": d, "value": v} for d, v in self.data[sid]]})


def test_fred_api_curve_uses_latest_date_where_every_series_has_a_value():
    data = {"DGS1MO": [("2026-10-22", "4.11"), ("2026-10-21", "4.10")],
            "DGS2": [("2026-10-22", "."), ("2026-10-21", "3.90")],
            "DGS10": [("2026-10-22", "4.25"), ("2026-10-21", "4.20")]}
    f = FredFetch(data)
    c = FredApi("K", fetch=f, series=[("DGS1MO", "1M"), ("DGS2", "2Y"), ("DGS10", "10Y")]).curve()
    assert c == {"date": "2026-10-21", "points": [("1M", 4.1), ("2Y", 3.9), ("10Y", 4.2)]}
    assert all("api_key=K" in u and "file_type=json" in u for u in f.calls)


def test_fred_api_without_key_raises_data_unavailable():
    with pytest.raises(DataUnavailable):
        FredApi("", fetch=FredFetch({})).curve()


def test_fred_api_error_message_never_contains_the_key():
    def boom(url, headers=None):
        raise DataUnavailable("fetch failed for " + url.split("?")[0])
    with pytest.raises(DataUnavailable) as e:
        FredApi("SECRETKEY", fetch=boom, series=[("DGS2", "2Y")]).curve()
    assert "SECRETKEY" not in str(e.value)


def test_yahoo_news_parses_rss_items():
    rss = ("<rss><channel><item><title>AAPL jumps</title><link>https://x.test/a</link>"
           "<pubDate>Mon, 26 Oct 2026 10:00:00 +0000</pubDate></item></channel></rss>")
    n = yahoo_news(rss)
    assert n == [{"headline": "AAPL jumps", "url": "https://x.test/a",
                  "source": "Yahoo Finance", "datetime": "Mon, 26 Oct 2026 10:00:00 +0000"}]


def test_yahoo_news_rejects_xml_with_doctype_entities():
    with pytest.raises(DataUnavailable):
        yahoo_news('<!DOCTYPE x [<!ENTITY a "b">]><rss></rss>')


def test_finnhub_recommendations_send_key_in_header_not_url():
    f = FakeFetch([{"period": "2026-10-01"}])
    Finnhub("SECRET", fetch=f).recommendations("aapl")
    url, headers = f.calls[0]
    assert "symbol=AAPL" in url and "SECRET" not in url
    assert headers["X-Finnhub-Token"] == "SECRET"


def test_finnhub_without_key_raises_data_unavailable():
    with pytest.raises(DataUnavailable):
        Finnhub("", fetch=FakeFetch({})).recommendations("AAPL")


def test_requests_identify_the_app_with_a_user_agent_unless_overridden():
    from sensa.providers import with_user_agent, USER_AGENT
    assert with_user_agent({})["User-Agent"] == USER_AGENT and "Abc" in USER_AGENT
    assert with_user_agent({"User-Agent": "x"})["User-Agent"] == "x"
    assert with_user_agent(None)["User-Agent"] == USER_AGENT
