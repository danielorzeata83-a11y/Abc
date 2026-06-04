"""Combinator sign-aware: ponderi ∝ IC-ul cauzal (semn inclus) al fiecarui
indicator. Verifica: lipsa look-ahead, recuperarea semnului (factor negativ
predictiv e intors), si ca evaluate_ensemble accepta weighting='ic'."""

import numpy as np

from markov.validation import ensemble


def _driver_world(n=600, beta=0.5, seed=0):
    """Randament next-day = beta*driver[t] + zgomot. Pret = produs cumulativ.
    Intoarce (prices, driver) -- driver[t] prezice randamentul t->t+1."""
    rng = np.random.default_rng(seed)
    driver = rng.normal(0, 1, n)
    ret = np.empty(n)
    ret[0] = 0.0
    ret[1:] = beta * 0.01 * driver[:-1] + rng.normal(0, 0.01, n - 1)
    prices = 100 * np.cumprod(1 + ret)
    return prices, driver


def test_sign_aware_recovers_sign_when_equal_weight_cancels():
    # feature bun ~ +driver, feature rau ~ -driver (fiecare cu zgomot propriu, ca
    # equal-weight sa nu degenereze in constanta). Equal-weight aproape se anuleaza;
    # sign-aware intoarce factorul invers-predictiv si aliniaza pozitiv.
    prices, driver = _driver_world()
    rng = np.random.default_rng(99)
    feats = {"good": driver + 0.3 * rng.normal(0, 1, len(driver)),
             "bad": -driver + 0.3 * rng.normal(0, 1, len(driver))}
    fwd = prices[1:] / prices[:-1] - 1.0

    eq = ensemble.equal_weight_signal(feats, causal=True)[:-1]
    sa = ensemble.sign_aware_signal(feats, prices)[:-1]
    m = np.isfinite(eq) & np.isfinite(sa) & np.isfinite(fwd)

    c_eq = np.corrcoef(eq[m], fwd[m])[0, 1]
    ic_eq = abs(c_eq) if np.isfinite(c_eq) else 0.0
    ic_sa = np.corrcoef(sa[m], fwd[m])[0, 1]
    assert ic_sa > 0.10
    assert ic_sa > ic_eq + 0.10


def test_sign_aware_no_lookahead():
    prices, driver = _driver_world(n=400, seed=3)
    feats = {"a": driver, "b": np.cumsum(driver)}
    full = ensemble.sign_aware_signal(feats, prices)
    t = 250
    trunc = ensemble.sign_aware_signal({k: v[:t + 1] for k, v in feats.items()},
                                       prices[:t + 1])
    assert np.allclose(full[t], trunc[t], equal_nan=True)


def test_evaluate_ensemble_ic_weighting_runs():
    prices, driver = _driver_world(seed=5)
    feats = {"good": driver, "bad": -driver}
    out = ensemble.evaluate_ensemble(feats, prices, weighting="ic")
    assert set(out) == {"net_return", "sharpe", "p_value", "n_days"}
    # pe lumea sintetica predictiva, sign-aware bate echivalentul equal-weight la Sharpe.
    eqm = ensemble.evaluate_ensemble(feats, prices, weighting="equal")
    assert out["sharpe"] > eqm["sharpe"]
