import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.company import CompanyInfo

EXCH = json.dumps({"fields": ["cik", "name", "ticker", "exchange"],
                   "data": [[1050441, "PEOPLES BANCORP INC", "PEBO", "Nasdaq"], [320193, "Apple Inc.", "AAPL", "Nasdaq"]]})
SUB = json.dumps({"sicDescription": "State Commercial Banks", "sic": "6022"})


class Sec:
    def __init__(self, shares=None, fail_sub=False):
        self.urls, self.fail_sub = [], fail_sub
        self.shares = shares

    def __call__(self, url):
        self.urls.append(url)
        if "company_tickers_exchange" in url:
            return EXCH
        if "submissions" in url:
            if self.fail_sub:
                raise DataUnavailable("sec down")
            return SUB
        raise DataUnavailable("unexpected")


class Shares:
    def get(self, t):
        return {"shares": 35_942_315, "as_of": "2026-07-29"}


def test_company_name_exchange_industry_and_share_count():
    c = CompanyInfo(Sec(), Shares()).get("pebo")
    assert c == {"ticker": "PEBO", "name": "PEOPLES BANCORP INC", "cik": "0001050441", "exchange": "Nasdaq",
                 "industry": "State Commercial Banks", "sic": "6022", "shares_outstanding": 35_942_315,
                 "shares_as_of": "2026-07-29"}


def test_unknown_ticker_gives_none_and_a_failing_detail_lookup_still_gives_the_basics():
    assert CompanyInfo(Sec(), Shares()).get("ZZZZ") is None
    c = CompanyInfo(Sec(fail_sub=True), Shares()).get("AAPL")
    assert c["name"] == "Apple Inc." and c["industry"] is None


def test_results_and_the_ticker_list_are_cached():
    sec = Sec()
    ci = CompanyInfo(sec, Shares())
    ci.get("PEBO"); ci.get("PEBO"); ci.get("AAPL")
    assert sum("company_tickers_exchange" in u for u in sec.urls) == 1 and sum("submissions" in u for u in sec.urls) == 2


def test_share_count_failure_is_not_fatal():
    class Bad:
        def get(self, t):
            raise DataUnavailable("x")
    assert CompanyInfo(Sec(), Bad()).get("PEBO")["shares_outstanding"] is None


def test_cik_lookup_uses_only_the_ticker_list():
    sec = Sec()
    ci = CompanyInfo(sec, Shares())
    assert ci.cik("pebo") == "0001050441" and ci.cik("ZZZZ") is None
    assert all("submissions" not in u for u in sec.urls)
