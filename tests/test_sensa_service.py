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


from sensa.service import gex


def test_gex_calls_positive_puts_negative_per_one_percent_move():
    spot = 100.0
    chain = [
        {"option_type": "call", "strike": 100.0, "gamma": 0.05, "open_interest": 10},
        {"option_type": "put", "strike": 95.0, "gamma": 0.02, "open_interest": 10},
    ]
    g = gex(chain, spot)
    # gamma * OI * 100 shares * spot^2 * 1%
    assert g["call_gex"] == 0.05 * 10 * 100 * 100 ** 2 * 0.01
    assert g["put_gex"] == -(0.02 * 10 * 100 * 100 ** 2 * 0.01)
    assert g["net_gex"] == g["call_gex"] + g["put_gex"]
    assert [r["strike"] for r in g["by_strike"]] == [95.0, 100.0]


def test_gex_ignores_rows_without_gamma_or_open_interest():
    g = gex([{"option_type": "call", "strike": 1.0, "gamma": None, "open_interest": 5},
             {"option_type": "put", "strike": 1.0, "gamma": 0.1, "open_interest": 0}], 50.0)
    assert g["net_gex"] == 0 and g["by_strike"] == []


def test_gex_keeps_call_and_put_totals_separate_when_same_strike():
    chain = [{"option_type": "call", "strike": 100.0, "gamma": 0.05, "open_interest": 10},
             {"option_type": "put", "strike": 100.0, "gamma": 0.04, "open_interest": 10}]
    g = gex(chain, 100.0)
    assert g["call_gex"] > 0 and g["put_gex"] < 0
    assert round(g["net_gex"], 6) == round(0.01 * 10 * 100 * 100 ** 2 * 0.01, 6)
    assert len(g["by_strike"]) == 1
