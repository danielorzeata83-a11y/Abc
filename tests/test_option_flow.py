import pytest

from sensa.option_flow import option_flow


def row(t, k, exp, vol=0, oi=100, iv=0.30, delta=0.5, bid=1.0, ask=1.2):
    return {"option_type": t, "strike": float(k), "expiration": exp, "volume": vol, "open_interest": oi, "iv": iv, "delta": delta, "bid": bid, "ask": ask, "gamma": 0.01}


def chain():
    return [row("call", 100, "2026-10-30", vol=400, oi=1000, iv=0.30, delta=0.52), row("put", 100, "2026-10-30", vol=600, oi=1000, iv=0.32, delta=-0.48),
            row("call", 110, "2026-10-30", vol=5000, oi=200, iv=0.35, delta=0.25, bid=2.0, ask=2.2),       # unusual: 25x open interest
            row("put", 90, "2026-10-30", vol=100, oi=300, iv=0.40, delta=-0.25),
            row("call", 100, "2026-11-20", vol=50, oi=500, iv=0.28, delta=0.55), row("put", 100, "2026-11-20", vol=50, oi=500, iv=0.30, delta=-0.45),
            row("call", 105, "2026-11-20", vol=10, oi=800, iv=0.27, delta=0.25), row("put", 95, "2026-11-20", vol=10, oi=800, iv=0.36, delta=-0.25)]


def test_totals_and_ratios():
    f = option_flow(100.0, chain(), "2026-10-26")
    assert f["call_volume"] == 400 + 5000 + 50 + 10 and f["put_volume"] == 600 + 100 + 50 + 10
    assert f["pc_volume_ratio"] == pytest.approx(760 / 5460, rel=1e-3) and f["pc_oi_ratio"] == pytest.approx((1000 + 300 + 500 + 800) / (1000 + 200 + 500 + 800), rel=1e-3)


def test_unusual_activity_needs_volume_far_above_open_interest_and_estimates_premium():
    f = option_flow(100.0, chain(), "2026-10-26")
    assert len(f["unusual"]) == 1
    u = f["unusual"][0]
    assert (u["type"], u["strike"], u["expiration"], u["volume"], u["open_interest"]) == ("call", 110.0, "2026-10-30", 5000, 200)
    assert u["premium"] == pytest.approx(5000 * 100 * 2.1) and u["dte"] == 4 and f["unusual_bias"] == pytest.approx(5000 * 100 * 2.1)


def test_term_structure_expected_move_and_skew():
    f = option_flow(100.0, chain(), "2026-10-26")
    assert [(t["expiration"], t["dte"]) for t in f["term"]] == [("2026-10-30", 4), ("2026-11-20", 25)]
    assert f["term"][0]["atm_iv_pct"] == pytest.approx(31.0)                                   # average of the 30% call and 32% put at the money
    em = f["expected_move"]
    assert em["expiration"] == "2026-10-30" and em["move_pct"] == pytest.approx(31.0 * (4 / 365) ** 0.5, rel=1e-3)
    assert f["skew"]["expiration"] == "2026-11-20" and f["skew"]["put_minus_call_pct"] == pytest.approx(9.0)      # 36% put vs 27% call at 25 delta


def test_plain_language_signals_and_empty_chain():
    f = option_flow(100.0, chain(), "2026-10-26")
    text = " | ".join(f["signals"])
    assert "put/call" in text.lower() and "unusual" in text.lower() and "call" in text.lower()
    assert option_flow(100.0, [], "2026-10-26") is None


def test_expired_contracts_are_ignored():
    c = chain() + [row("call", 100, "2026-10-20", vol=99999, oi=1)]
    assert option_flow(100.0, c, "2026-10-26")["call_volume"] == 5460
