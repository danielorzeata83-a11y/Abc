import numpy as np
import pandas as pd
import pytest

from sensa.signal_history import MAPPING, build_samples, summarize_evidence

N, DAYS = 30, 800
DATES = list(pd.bdate_range("2020-01-01", periods=DAYS).strftime("%Y-%m-%d"))
SIGNAL_IDX = [260 + 63 * k for k in range(8)]


def world(seed=0, strength=0.12):
    """prices where each quarter's forward 63-day return is planted from that quarter's fund signal"""
    rng = np.random.default_rng(seed)
    tickers = [f"T{i}" for i in range(N)]
    closes = {t: [] for t in tickers}
    overviews = []
    r = rng.normal(0.0003, 0.01, size=(DAYS, N))
    for k, idx in enumerate(SIGNAL_IDX):
        s = rng.normal(size=N)
        planted = strength * s * 0.3 + rng.normal(0, 0.02, N)                          # total return over the next 63 days
        r[idx:idx + 63] = (1 + planted) ** (1 / 63) - 1
        overviews.append({"period": f"q{k}", "signal_date": DATES[idx], "stocks": [
            {"ticker": t, "kind": "stock", "holders": 60, "holders_prev": int(round(60 - 10 * s[i])) if int(round(60 - 10 * s[i])) > 0 else 1,
             "active_flow": float(s[i] * 1e8), "value": 1e10, "new": 0, "exited": 0, "gone": False, "new_listing": False} for i, t in enumerate(tickers)]})
    px = 100 * np.cumprod(1 + r, axis=0)
    return overviews, {t: (DATES, list(px[:, i])) for i, t in enumerate(tickers)}


def test_fund_signals_are_built_per_quarter_with_point_in_time_forward_returns():
    ov, closes = world()
    samples = build_samples(ov, [], lambda t: closes.get(t), horizons=(63,))
    assert {"smart_money", "holders_change", "active_flow", "momentum_12_1", "trend", "quality_sharpe", "insider_net"} <= set(samples)
    d0 = DATES[SIGNAL_IDX[0]]
    row = {x["ticker"]: x for x in samples["smart_money"][d0]}["T3"]
    i = DATES.index(d0)
    assert row["fwd"][63] == pytest.approx(closes["T3"][1][i + 63] / closes["T3"][1][i] - 1)


def test_a_planted_signal_is_found_and_its_weight_survives():
    ov, closes = world(strength=1.0)
    samples = build_samples(ov, [], lambda t: closes.get(t), horizons=(63,))
    ev = summarize_evidence(samples, horizons=(63,), defaults={"smart": 0.3, "momentum": 0.25, "trend": 0.1, "quality": 0.15, "insider": 0.15, "politician": 0.05})
    s = ev["signals"]["smart_money"]
    assert s["stats"][63]["mean_ic"] > 0.2 and s["verdict"] == "works" and ev["weights"]["evidence"]["smart"] >= ev["weights"]["default"]["smart"] * 0.99
    assert ev["weights"]["evidence"]["politician"] > 0 and ev["n_signal_dates"] == 8
    assert MAPPING["smart_money"] == "smart"


def test_price_features_never_use_data_after_the_signal_date():
    ov, closes = world()
    base = build_samples(ov, [], lambda t: closes.get(t), horizons=(63,))
    cut = SIGNAL_IDX[3]
    tampered = {t: (d, c[:cut + 1] + [c[cut] * 5] * (len(c) - cut - 1)) for t, (d, c) in closes.items()}       # future wrecked after quarter 3's date
    new = build_samples(ov, [], lambda t: tampered.get(t), horizons=(63,))
    d3 = DATES[cut]
    a = {x["ticker"]: x["value"] for x in base["momentum_12_1"][d3]}
    b = {x["ticker"]: x["value"] for x in new["momentum_12_1"][d3]}
    assert a == b


def test_insider_signal_uses_only_trades_filed_before_the_date_in_the_last_30_days():
    ov, closes = world()
    d = DATES[SIGNAL_IDX[2]]
    trades = [{"symbol": "T1", "owner": "a", "side": "buy", "value": 500000.0, "filed": DATES[SIGNAL_IDX[2] - 5], "date": DATES[SIGNAL_IDX[2] - 6], "plan": False},
              {"symbol": "T2", "owner": "b", "side": "buy", "value": 500000.0, "filed": DATES[SIGNAL_IDX[2] + 3], "date": DATES[SIGNAL_IDX[2]], "plan": False},        # filed after: unknown on that day
              {"symbol": "T3", "owner": "c", "side": "buy", "value": 500000.0, "filed": DATES[SIGNAL_IDX[2] - 80], "date": DATES[SIGNAL_IDX[2] - 81], "plan": False}]  # too old
    samples = build_samples(ov, trades, lambda t: closes.get(t), horizons=(63,))
    row = {x["ticker"]: x["value"] for x in samples["insider_net"][d]}
    assert row["T1"] > 0 and row["T2"] == 0 and row["T3"] == 0
