import numpy as np
import pandas as pd
import pytest

from sensa.picks_backtest import make_rank_strategy, rank_backtest


def prices(n=900, k=14, seed=0, vol=0.011):
    rng = np.random.default_rng(seed)
    drift = np.linspace(-0.0004, 0.0012, k)                      # persistent differences: momentum has something to find
    R = rng.normal(drift, vol, size=(n, k))
    idx = [pd.Timestamp((20000 + i) * 86400, unit="s").strftime("%Y-%m-%d") for i in range(n)]
    return pd.DataFrame(100 * np.cumprod(1 + R, axis=0), index=idx, columns=[f"S{i}" for i in range(k)])


def test_strategy_picks_the_strongest_uptrending_names_with_capped_inverse_vol_weights():
    P = prices(vol=0.002)                                            # clear signal, so the test is about the mechanics
    R = P.pct_change().dropna().iloc[:400]
    w = make_rank_strategy(top_n=5, max_weight=0.3)(R, None)
    assert (w > 0).sum() == 5 and w.sum() == pytest.approx(1.0) and w.max() <= 0.3 + 1e-9
    chosen = set(np.where(w > 0)[0])
    assert chosen <= set(range(7, 14))                               # only names from the high-drift end of the universe


def test_a_universe_in_a_downtrend_falls_back_to_equal_weights_rather_than_inventing_picks():
    R = pd.DataFrame(np.full((320, 4), -0.002), index=[f"d{i}" for i in range(320)])
    w = make_rank_strategy(top_n=2)(R, None)
    assert np.allclose(w, 0.25)


def test_backtest_reports_strategy_equal_weight_and_benchmark_on_identical_days_with_costs():
    P = prices(seed=3, vol=0.002)
    spy = pd.Series(100 * np.cumprod(1 + np.random.default_rng(9).normal(0.0003, 0.008, len(P))), index=P.index)
    r = rank_backtest(P, benchmark=spy, top_n=5)
    m = r["models"]
    assert set(m) == {"picks_rule", "equal_weight", "benchmark"} and len({x["days"] for x in m.values()}) == 1
    assert m["picks_rule"]["ann_return"] > m["equal_weight"]["ann_return"]       # with a clear, persistent signal the rule must find it
    assert m["picks_rule"]["cost_total"] > 0 and r["periods"]["start"] < r["periods"]["end"] and len(r["curves"]["dates"]) <= 300 and {len(v) for v in r["curves"]["models"].values()} == {len(r["curves"]["dates"])}
    assert "survivorship" in r["caveat"].lower() and r["params"] == {"top_n": 5, "window": 300, "every": 21, "cost_bps": 10.0, "max_weight": 0.2}


def test_too_little_history_is_a_clear_error():
    with pytest.raises(ValueError, match="history"):
        rank_backtest(prices(n=330))


def test_with_noisy_prices_the_rule_may_lose_to_equal_weights_and_the_report_just_says_so():
    r = rank_backtest(prices(seed=3), top_n=5)                                  # realistic noise: momentum is a weak signal
    m = r["models"]
    assert m["picks_rule"]["sharpe"] is not None and m["equal_weight"]["sharpe"] is not None and m["benchmark"]["days"] == m["picks_rule"]["days"]
