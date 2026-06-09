import numpy as np
from markov.validation import ensemble


def test_zscore_causal_no_lookahead():
    rng = np.random.default_rng(0)
    x = rng.normal(size=50)
    z = ensemble.zscore_causal(x)
    x2 = x.copy(); x2[30:] += 100.0
    z2 = ensemble.zscore_causal(x2)
    assert abs(z[20] - z2[20]) < 1e-9


def test_equal_weight_is_mean_of_zscores():
    x = np.arange(30.0)
    feats = {"a": x, "b": x}
    sig = ensemble.equal_weight_signal(feats, causal=False)
    za = (x - x.mean()) / x.std()
    assert np.allclose(sig[5:], za[5:], atol=1e-9)


def test_evaluate_ensemble_detects_real_signal():
    rng = np.random.default_rng(3)
    n = 400
    rets = rng.normal(0, 0.01, size=n)
    prices = 100 * np.cumprod(1 + rets)
    look = np.empty(n); look[:-1] = rets[1:]; look[-1] = 0.0
    feats = {"oracle": look}
    res = ensemble.evaluate_ensemble(feats, prices, warmup=20)
    assert res["net_return"] > 0
    assert res["p_value"] < 0.05


def test_evaluate_ensemble_noise_not_significant():
    rng = np.random.default_rng(4)
    n = 400
    prices = 100 * np.cumprod(1 + rng.normal(0, 0.01, size=n))
    feats = {"noise": rng.normal(size=n)}
    res = ensemble.evaluate_ensemble(feats, prices, warmup=20)
    assert res["p_value"] > 0.05


def test_regime_gate_zeroes_position_outside_target_regime():
    """Cu semnal-oracol dar gated pe 'meanrev', zilele etichetate 'trend' nu
    trebuie sa contribuie: pozitia (deci randamentul) e zero acolo."""
    rng = np.random.default_rng(3)
    n = 400
    rets = rng.normal(0, 0.01, size=n)
    prices = 100 * np.cumprod(1 + rets)
    look = np.empty(n); look[:-1] = rets[1:]; look[-1] = 0.0
    feats = {"oracle": look}
    labels = np.array(["trend"] * n, dtype=object)      # totul 'trend'
    res = ensemble.evaluate_ensemble(feats, prices, warmup=20,
                                     regime_labels=labels, active_regime="meanrev")
    # niciun pas in regimul tinta -> fara expunere -> randament net ~0
    assert abs(res["net_return"]) < 1e-9
