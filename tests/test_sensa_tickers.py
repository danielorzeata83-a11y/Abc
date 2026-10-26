import json

import pytest

from sensa.thirteenf import Figi
from sensa.tickers import TickerResolver
from tests.test_sensa_holders import make_zip
from sensa.holders import build_holders_db


@pytest.fixture
def db(tmp_path):
    cur, prev = str(tmp_path / "q2.zip"), str(tmp_path / "q1.zip")
    rows = [("PEOPLES BANCORP INC", "709789101", 100, 10), ("PEOPLES BANCORP NC INC", "710577107", 50, 5),
            ("APPLE INC", "037833100", 900, 9)]
    make_zip(cur, "2026-06-30", {"0000000001": ("A1", "Alpha", 9000, rows)})
    make_zip(prev, "2026-03-31", {"0000000001": ("B1", "Alpha", 9000, rows)})
    path = str(tmp_path / "holders.db")
    build_holders_db(cur, prev, "2026-06-30", "2026-03-31", path)
    return path


class FakeOpenFigi:
    """Answers both CUSIP lookups and TICKER name lookups."""
    TICKERS = {"PEBO": "PEOPLES BANCORP INC/OH", "AAPL": "APPLE INC", "PEBK": "PEOPLES BANCORP NC INC",
               "ZZZZ": "NOTHING LIKE IT CORP", "HOLD": "PEOPLES BANCORP HOLDINGS INC"}
    CUSIPS = {"709789101": "PEBO", "710577107": "PEBK", "037833100": "AAPL"}

    def __init__(self):
        self.calls = []

    def __call__(self, url, payload, headers=None):
        self.calls.append(payload)
        out = []
        for p in payload:
            if p["idType"] == "TICKER":
                name = self.TICKERS.get(p["idValue"])
                out.append({"data": [{"name": name, "ticker": p["idValue"], "exchCode": "US", "securityType": "Common Stock"}]}
                           if name else {"warning": "No identifier found."})
            else:
                t = self.CUSIPS.get(p["idValue"])
                out.append({"data": [{"ticker": t, "exchCode": "US", "securityType": "Common Stock"}]} if t else {"warning": "x"})
        return json.dumps(out)


def make(db, tmp_path, post=None, cache=True):
    post = post or FakeOpenFigi()
    figi = Figi(post, cache_path=str(tmp_path / "figi.json"))
    return TickerResolver(db, post, figi, cache_path=str(tmp_path / "tickers.json") if cache else None), post


def test_a_ticker_is_resolved_through_its_name_and_confirmed_by_the_reverse_lookup(db, tmp_path):
    r, _ = make(db, tmp_path)
    assert r.cusip("PEBO") == "709789101"                  # "/OH" suffix ignored; PEBK's longer name must not win


def test_lowercase_input_is_accepted(db, tmp_path):
    r, _ = make(db, tmp_path)
    assert r.cusip("aapl") == "037833100"


def test_a_shorter_name_prefix_is_tried_when_the_full_name_matches_nothing(db, tmp_path):
    r, post = make(db, tmp_path)
    post.TICKERS["PEBO"] = "PEOPLES BANCORP HOLDINGS INC"
    assert r.cusip("PEBO") == "709789101"


def test_a_candidate_whose_ticker_differs_is_not_accepted(db, tmp_path):
    r, _ = make(db, tmp_path)
    assert r.cusip("HOLD") is None                         # name matches the PEOPLES issuers, but their tickers are PEBO/PEBK


def test_unknown_or_malformed_tickers_give_none_and_malformed_ones_cost_no_request(db, tmp_path):
    r, post = make(db, tmp_path)
    assert r.cusip("ZZZZ") is None
    n = len(post.calls)
    assert r.cusip("A B") is None and r.cusip("%") is None and r.cusip("") is None and len(post.calls) == n


def test_a_ticker_already_in_the_cusip_cache_needs_no_name_lookup(db, tmp_path):
    post = FakeOpenFigi()
    figi = Figi(post, cache_path=str(tmp_path / "figi.json"))
    figi.info(["037833100"])
    n = len(post.calls)
    r = TickerResolver(db, post, figi)
    assert r.cusip("AAPL") == "037833100" and len(post.calls) == n


def test_found_tickers_are_remembered_on_disk(db, tmp_path):
    r, _ = make(db, tmp_path)
    r.cusip("PEBO")
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
    again = TickerResolver(db, boom, Figi(boom), cache_path=str(tmp_path / "tickers.json"))
    assert again.cusip("PEBO") == "709789101"
