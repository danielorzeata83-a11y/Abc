import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.providers import Finnhub, TradierSandbox, treasury_curve


class FakeFetch:
    def __init__(self, body):
        self.body, self.calls = body, []

    def __call__(self, url, headers=None):
        self.calls.append((url, headers or {}))
        return self.body if isinstance(self.body, str) else json.dumps(self.body)


def test_finnhub_quote_maps_fields_and_sends_key_in_header_not_url():
    f = FakeFetch({"c": 110.5, "pc": 100.0, "h": 111, "l": 99, "o": 101, "t": 1})
    q = Finnhub("SECRET", fetch=f).quote("aapl")
    assert q == {"price": 110.5, "prev_close": 100.0}
    url, headers = f.calls[0]
    assert "symbol=AAPL" in url and "SECRET" not in url
    assert headers["X-Finnhub-Token"] == "SECRET"


def test_finnhub_without_key_raises_data_unavailable():
    with pytest.raises(DataUnavailable):
        Finnhub("", fetch=FakeFetch({})).quote("AAPL")


def test_tradier_chain_normalises_single_option_object_to_list():
    body = {"options": {"option": {"symbol": "AAPL261120C00200000",
                                   "option_type": "call", "strike": 200.0,
                                   "volume": 3, "open_interest": 9,
                                   "greeks": {"delta": 0.5}}}}
    f = FakeFetch(body)
    chain = TradierSandbox("TOK", fetch=f).chain("aapl", "2026-11-20")
    assert isinstance(chain, list) and chain[0]["strike"] == 200.0
    url, headers = f.calls[0]
    assert "sandbox.tradier.com/v1/markets/options/chains" in url
    assert "greeks=true" in url and "expiration=2026-11-20" in url
    assert headers["Authorization"] == "Bearer TOK"


def test_tradier_chain_empty_when_no_options():
    assert TradierSandbox("T", fetch=FakeFetch({"options": None})).chain("X", "2026-11-20") == []


def test_treasury_curve_parses_latest_row_in_maturity_order():
    csv = ("Date,1 Mo,2 Yr,10 Yr,30 Yr\n"
           "10/23/2026,4.50,4.00,4.20,4.60\n"
           "10/22/2026,4.40,3.90,4.10,4.50\n")
    c = treasury_curve(csv)
    assert c["date"] == "10/23/2026"
    assert c["points"] == [("1 Mo", 4.5), ("2 Yr", 4.0), ("10 Yr", 4.2), ("30 Yr", 4.6)]


def test_treasury_curve_picks_latest_date_across_month_boundary():
    csv = ("Date,2 Yr\n10/30/2026,3.90\n11/02/2026,4.00\n")
    assert treasury_curve(csv)["date"] == "11/02/2026"
