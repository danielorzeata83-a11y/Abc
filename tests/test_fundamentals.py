import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.fundamentals import Fundamentals, parse_company_facts


def fact(start, end, val, form, filed, fp=""):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "fp": fp, "fy": int(end[:4])}


def inst(end, val, form="10-Q", filed="2026-08-01"):
    return {"end": end, "val": val, "form": form, "filed": filed, "fp": "Q3", "fy": int(end[:4])}


def facts():
    rev = [fact("2023-10-01", "2024-09-30", 800.0, "10-K", "2024-11-01"), fact("2024-10-01", "2025-09-30", 1000.0, "10-K", "2026-11-01"),
           fact("2025-10-01", "2026-06-30", 900.0, "10-Q", "2026-08-01"), fact("2024-10-01", "2025-06-30", 700.0, "10-Q", "2025-08-01"),
           fact("2026-04-01", "2026-06-30", 300.0, "10-Q", "2026-08-01")]
    return {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": rev}},
        "NetIncomeLoss": {"units": {"USD": [fact("2024-10-01", "2025-09-30", 100.0, "10-K", "2026-11-01"), fact("2025-10-01", "2026-06-30", 90.0, "10-Q", "2026-08-01"),
                                            fact("2024-10-01", "2025-06-30", 60.0, "10-Q", "2025-08-01")]}},
        "OperatingIncomeLoss": {"units": {"USD": [fact("2024-10-01", "2025-09-30", 150.0, "10-K", "2026-11-01"), fact("2025-10-01", "2026-06-30", 135.0, "10-Q", "2026-08-01"),
                                                  fact("2024-10-01", "2025-06-30", 90.0, "10-Q", "2025-08-01")]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [fact("2024-10-01", "2025-09-30", 2.0, "10-K", "2026-11-01"), fact("2025-10-01", "2026-06-30", 1.8, "10-Q", "2026-08-01"),
                                                             fact("2024-10-01", "2025-06-30", 1.2, "10-Q", "2025-08-01")]}},
        "StockholdersEquity": {"units": {"USD": [inst("2026-03-31", 400.0), inst("2026-06-30", 500.0)]}},
        "LongTermDebt": {"units": {"USD": [inst("2026-06-30", 250.0)]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [inst("2026-06-30", 100.0)]}}}}}


def test_ttm_is_last_fiscal_year_plus_this_year_to_date_minus_the_same_period_a_year_ago():
    m = parse_company_facts(facts())
    assert m["revenue_ttm"] == pytest.approx(1000 + 900 - 700) and m["net_income_ttm"] == pytest.approx(100 + 90 - 60)
    assert m["eps_ttm"] == pytest.approx(2.0 + 1.8 - 1.2) and m["period_end"] == "2026-06-30"


def test_margins_growth_and_balance_sheet_ratios():
    m = parse_company_facts(facts())
    assert m["op_margin_pct"] == pytest.approx((150 + 135 - 90) / 1200 * 100) and m["net_margin_pct"] == pytest.approx(130 / 1200 * 100)
    assert m["revenue_growth_pct"] == pytest.approx((1000 / 800 - 1) * 100)                    # last fiscal year vs the one before
    assert m["roe_pct"] == pytest.approx(130 / 500 * 100) and m["debt_to_equity"] == pytest.approx(250 / 500) and m["net_debt"] == pytest.approx(150.0)


def test_only_a_fiscal_year_is_enough_and_missing_concepts_stay_none():
    f = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [fact("2025-01-01", "2025-12-31", 500.0, "10-K", "2026-02-01")]}}}}}
    m = parse_company_facts(f)
    assert m["revenue_ttm"] == 500.0 and m["net_income_ttm"] is None and m["op_margin_pct"] is None and m["debt_to_equity"] is None


def test_restated_figures_use_the_latest_filing_and_alternative_revenue_names_work():
    f = facts()
    f["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"] = {"units": {"USD": [fact("2024-10-01", "2025-09-30", 1111.0, "10-K", "2026-11-01"),
                                                                                                     fact("2024-10-01", "2025-09-30", 999.0, "10-K", "2026-10-01")]}}
    del f["facts"]["us-gaap"]["Revenues"]
    assert parse_company_facts(f)["revenue_ttm"] == 1111.0


def test_nothing_parseable_returns_none():
    assert parse_company_facts({"facts": {}}) is None and parse_company_facts({}) is None


class Sec:
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if "CIK0000000001" in url:
            return json.dumps(facts())
        raise DataUnavailable("404")


def test_service_adds_price_based_ratios_caches_to_disk_and_gives_none_for_funds(tmp_path):
    sec = Sec()
    svc = Fundamentals(sec, lambda t: "0000000001" if t == "AAA" else None, str(tmp_path / "f.json"))
    m = svc.get("aaa", price=26.0)
    assert m["pe"] == pytest.approx(26.0 / 2.6) and m["earnings_yield_pct"] == pytest.approx(10.0) and m["market_cap"] is None
    svc.get("AAA", price=30.0)
    assert len(sec.urls) == 1 and svc.get("AAA", price=26.0)["pe"] == pytest.approx(10.0)
    assert svc.get("ETF", price=10.0) is None
    again = Fundamentals(lambda u: (_ for _ in ()).throw(AssertionError("network")), lambda t: "0000000001", str(tmp_path / "f.json"))
    assert again.get("AAA", price=26.0)["revenue_ttm"] == pytest.approx(1200)


def test_unprofitable_companies_have_no_pe_and_a_failing_download_is_none():
    f = facts()
    f["facts"]["us-gaap"]["EarningsPerShareDiluted"]["units"]["USD/shares"] = [fact("2024-10-01", "2025-09-30", -1.0, "10-K", "2026-11-01")]
    svc = Fundamentals(lambda u: json.dumps(f), lambda t: "0000000001", None)
    m = svc.get("AAA", price=10.0)
    assert m["pe"] is None and m["eps_ttm"] == -1.0 and m["earnings_yield_pct"] == pytest.approx(-10.0)
    bad = Fundamentals(Sec(), lambda t: "0000000009", None)
    assert bad.get("ZZZ", price=1.0) is None
