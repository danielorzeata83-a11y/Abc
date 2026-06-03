"""Prognoza OOS de volatilitate: oracol -> IC mare; zgomot -> IC ~0; pooling."""

import numpy as np

from markov.validation.vol_forecast import (evaluate_vol_forecast,
                                            pooled_vol_forecast)
from markov.validation.dataset import forward_realized_vol


def _vol_clustered_close(n=400, seed=0):
    """Pret cu vol care se grupeaza (AR pe log-vol) -> vol prezicibila."""
    rng = np.random.default_rng(seed)
    logv = np.zeros(n)
    for t in range(1, n):
        logv[t] = 0.95 * logv[t - 1] + rng.normal(0, 0.3)
    vol = 0.01 * np.exp(logv)
    rets = rng.normal(0, 1, n) * vol
    return 100 * np.cumprod(1 + rets)


def test_oracle_feature_high_ic():
    close = _vol_clustered_close()
    tgt = forward_realized_vol(close, (5,))[5]
    res = evaluate_vol_forecast({"oracle": tgt}, close, horizon=5)
    assert res["ic"] > 0.8                       # feature = tinta -> IC ~1
    assert res["n"] > 100


def test_noise_feature_near_zero_ic():
    close = _vol_clustered_close(seed=1)
    rng = np.random.default_rng(2)
    res = evaluate_vol_forecast({"noise": rng.normal(size=len(close))},
                                close, horizon=5)
    assert abs(res["ic"]) < 0.15                 # zgomot -> fara putere


def test_pooled_averages_over_symbols():
    c1 = _vol_clustered_close(seed=3)
    c2 = _vol_clustered_close(seed=4)
    feats = {"A": {"oracle": forward_realized_vol(c1, (5,))[5]},
             "B": {"oracle": forward_realized_vol(c2, (5,))[5]}}
    close = {"A": c1, "B": c2}
    pooled = pooled_vol_forecast(feats, close, ["oracle"], horizon=5)
    assert pooled["ic"] > 0.8
    assert pooled["n"] > 200                      # suma pe ambele simboluri
