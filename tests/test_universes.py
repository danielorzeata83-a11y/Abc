"""Tests for custom universe resolution.

resolve_universe accepts a named universe (TECH, SP500), a comma list, or
a @file path, and intersects it with the tickers actually available in the
data, preserving a stable order.
"""

import pytest

from markov.universes import resolve_universe, NAMED_UNIVERSES


def test_named_tech_intersected_with_available():
    available = ["AAPL", "MSFT", "NVDA", "XOM", "JPM"]
    out = resolve_universe("TECH", available)
    assert "AAPL" in out and "NVDA" in out
    assert "XOM" not in out  # not a tech name
    assert all(t in available for t in out)


def test_sp500_means_all_available():
    available = ["AAPL", "XOM", "JPM"]
    assert set(resolve_universe("SP500", available)) == set(available)


def test_comma_list():
    available = ["AAPL", "MSFT", "NVDA"]
    out = resolve_universe("AAPL,NVDA", available)
    assert out == ["AAPL", "NVDA"]


def test_file_list(tmp_path):
    f = tmp_path / "u.txt"
    f.write_text("AAPL\nNVDA\n# comment\nMSFT\n")
    out = resolve_universe(f"@{f}", ["AAPL", "MSFT", "NVDA", "JPM"])
    assert out == ["AAPL", "NVDA", "MSFT"]


def test_unknown_ticker_in_list_dropped_with_available():
    out = resolve_universe("AAPL,ZZZ", ["AAPL", "MSFT"])
    assert out == ["AAPL"]


def test_empty_resolution_raises():
    with pytest.raises(ValueError):
        resolve_universe("ZZZ,YYY", ["AAPL", "MSFT"])


def test_named_universes_registry_nonempty():
    assert "TECH" in NAMED_UNIVERSES and len(NAMED_UNIVERSES["TECH"]) > 5


def test_crypto_universe_registered_and_lowercase():
    assert "CRYPTO" in NAMED_UNIVERSES
    out = resolve_universe("CRYPTO", ["btc", "eth", "ltc", "xxx"])
    assert "btc" in out and "eth" in out and "xxx" not in out


def test_candidate_tickers_named_and_list_and_file(tmp_path):
    from markov.universes import candidate_tickers
    assert candidate_tickers("CRYPTO")[:1] == ["btc"]
    assert candidate_tickers("AAPL,NVDA") == ["AAPL", "NVDA"]
    f = tmp_path / "u.txt"; f.write_text("AAPL\nNVDA\n")
    assert candidate_tickers(f"@{f}") == ["AAPL", "NVDA"]
    # SP500 cannot be enumerated without data -> None
    assert candidate_tickers("SP500") is None
