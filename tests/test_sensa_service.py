from sensa.service import movers


def test_movers_ranks_gainers_and_losers_by_percent_change():
    quotes = {
        "AAA": {"price": 110.0, "prev_close": 100.0},   # +10%
        "BBB": {"price": 95.0, "prev_close": 100.0},    # -5%
        "CCC": {"price": 101.0, "prev_close": 100.0},   # +1%
        "DDD": {"price": 80.0, "prev_close": 100.0},    # -20%
    }
    out = movers(quotes, n=2)
    assert [r["symbol"] for r in out["gainers"]] == ["AAA", "CCC"]
    assert [r["symbol"] for r in out["losers"]] == ["DDD", "BBB"]
    assert out["gainers"][0]["change_pct"] == 10.0


def test_movers_skips_quotes_without_a_usable_previous_close():
    quotes = {"AAA": {"price": 10.0, "prev_close": 0}, "BBB": {"price": 5.0}}
    out = movers(quotes, n=5)
    assert out == {"gainers": [], "losers": []}


from sensa.service import analyst_consensus, cp_ratio


def test_analyst_consensus_uses_latest_period_and_computes_verdict():
    trends = [
        {"period": "2026-09-01", "strongBuy": 5, "buy": 10, "hold": 4, "sell": 1, "strongSell": 0},
        {"period": "2026-10-01", "strongBuy": 10, "buy": 20, "hold": 5, "sell": 3, "strongSell": 2},
    ]
    c = analyst_consensus(trends)
    assert (c["buy"], c["hold"], c["sell"]) == (30, 5, 5)
    assert c["verdict"] == "Buy"
    assert c["period"] == "2026-10-01"


def test_analyst_consensus_is_none_without_data():
    assert analyst_consensus([]) is None


def test_cp_ratio_from_volume_and_open_interest():
    chain = [
        {"option_type": "call", "volume": 300, "open_interest": 1000},
        {"option_type": "call", "volume": 100, "open_interest": 500},
        {"option_type": "put", "volume": 200, "open_interest": 750},
    ]
    r = cp_ratio(chain)
    assert r["call_volume"] == 400 and r["put_volume"] == 200
    assert r["volume_ratio"] == 2.0
    assert r["oi_ratio"] == 2.0


def test_cp_ratio_without_puts_has_no_ratio():
    r = cp_ratio([{"option_type": "call", "volume": 5, "open_interest": 5}])
    assert r["volume_ratio"] is None and r["oi_ratio"] is None
