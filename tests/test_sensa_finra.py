from datetime import date

import pytest

from markov.data_providers import DataUnavailable
from sensa.finra import Finra

BODY = ("Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n"
        "20261023|AAPL|8000.5|10|20000.0|B,Q,N\n"
        "20261023|NVDA|0|0|0|B,Q,N\n")


def serve_only(day_str):
    calls = []

    def fetch(url, headers=None):
        calls.append(url)
        if day_str in url:
            return BODY
        raise DataUnavailable("403")
    fetch.calls = calls
    return fetch


def test_short_volume_uses_latest_published_day_skipping_weekend():
    f = serve_only("20261023")                       # Friday; today is Monday
    out = Finra(fetch=f).load(date(2026, 10, 26))
    assert out["date"] == "2026-10-23"
    assert f.calls[0].endswith("CNMSshvol20261026.txt")   # tried today first


def test_short_ratio_and_unknown_symbol():
    d = Finra(fetch=serve_only("20261023")).load(date(2026, 10, 26))
    aapl = Finra.lookup(d, "aapl")
    assert aapl["short_volume"] == 8000.5 and aapl["total_volume"] == 20000.0
    assert aapl["short_ratio"] == 0.4
    assert Finra.lookup(d, "NVDA")["short_ratio"] is None     # zero total volume
    assert Finra.lookup(d, "ZZZZ") is None


def test_raises_when_nothing_published_in_the_last_week():
    def never(url, headers=None):
        raise DataUnavailable("403")
    with pytest.raises(DataUnavailable):
        Finra(fetch=never).load(date(2026, 10, 26))
