import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.shares_out import SharesOutstanding

TICKERS = json.dumps({"0": {"cik_str": 1050441, "ticker": "PEBO", "title": "PEOPLES BANCORP INC"},
                      "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}})


def concept(*facts):
    return json.dumps({"units": {"shares": [{"end": e, "val": v, "filed": f, "form": "10-Q"} for e, v, f in facts]}})


class FakeSec:
    def __init__(self, concepts):
        self.concepts, self.urls = concepts, []

    def __call__(self, url, headers=None):
        self.urls.append(url)
        if "company_tickers" in url:
            return TICKERS
        for cik, body in self.concepts.items():
            if f"CIK{cik:010d}" in url:
                return body
        raise DataUnavailable("404")


def test_latest_reported_count_is_used(tmp_path):
    f = FakeSec({1050441: concept(("2026-03-31", 35_000_000, "2026-05-01"), ("2026-06-30", 35_500_000, "2026-08-01"))})
    s = SharesOutstanding(f, str(tmp_path / "so.json"))
    assert s.get("pebo") == {"shares": 35_500_000, "as_of": "2026-06-30"}


def test_two_different_counts_on_the_latest_date_mean_several_share_classes_so_no_count(tmp_path):
    f = FakeSec({320193: concept(("2026-06-30", 100, "2026-08-01"), ("2026-06-30", 40, "2026-08-01"))})
    assert SharesOutstanding(f, str(tmp_path / "so.json")).get("AAPL") is None


def test_the_same_count_filed_twice_is_not_ambiguous(tmp_path):
    f = FakeSec({320193: concept(("2026-06-30", 100, "2026-08-01"), ("2026-06-30", 100, "2026-08-02"))})
    assert SharesOutstanding(f, str(tmp_path / "so.json")).get("AAPL")["shares"] == 100


def test_unknown_ticker_or_missing_facts_give_none(tmp_path):
    f = FakeSec({})
    s = SharesOutstanding(f, str(tmp_path / "so.json"))
    assert s.get("NOPE") is None and s.get("AAPL") is None


def test_results_are_cached_on_disk_and_the_ticker_list_is_fetched_once(tmp_path):
    f = FakeSec({1050441: concept(("2026-06-30", 5, "2026-08-01")), 320193: concept(("2026-06-30", 7, "2026-08-01"))})
    path = str(tmp_path / "so.json")
    s = SharesOutstanding(f, path)
    s.get("PEBO"); s.get("AAPL"); s.get("PEBO")
    assert sum("company_tickers" in u for u in f.urls) == 1 and sum("PEBO" in u or "1050441" in u for u in f.urls) == 1
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
    assert SharesOutstanding(boom, path).get("AAPL")["shares"] == 7
