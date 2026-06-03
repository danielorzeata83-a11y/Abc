"""Ansamblu de indicatori (pasul E). Z-score CAUZAL (doar trecut) pentru a evita
look-ahead-ul; full-sample doar pentru afisare descriptiva. Evaluarea ruleaza prin
backtest.walk_forward + significance.permutation_test. NU este consiliere de investitii.
"""

import numpy as np

from markov.backtest import walk_forward
from markov.significance import permutation_test


def zscore_causal(x):
    """Standardizare expandabila: z[t] = (x[t]-mean(x[:t+1]))/std(x[:t+1]).

    Foloseste DOAR trecutul (inclusiv t). nan unde <2 puncte finite sau std==0.
    """
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    for t in range(len(x)):
        past = x[: t + 1]
        fin = past[np.isfinite(past)]
        if len(fin) >= 2 and fin.std(ddof=0) > 0:
            out[t] = (x[t] - fin.mean()) / fin.std(ddof=0)
    return out


def _zscore_full(x):
    x = np.asarray(x, dtype=float)
    fin = x[np.isfinite(x)]
    if len(fin) < 2 or fin.std(ddof=0) == 0:
        return np.full(len(x), np.nan)
    return (x - fin.mean()) / fin.std(ddof=0)


def equal_weight_signal(features, causal=True):
    """Media (nanmean) z-score-urilor indicatorilor -> un singur semnal aliniat."""
    fn = zscore_causal if causal else _zscore_full
    zs = np.column_stack([fn(np.asarray(v, dtype=float)) for v in features.values()])
    with np.errstate(invalid="ignore"):
        return np.nanmean(zs, axis=1)


def evaluate_ensemble(features, prices, warmup=20, cost=0.0, n_perm=1000, seed=0):
    """Construieste semnalul cauzal -> strategie walk-forward -> metrici OOS.

    Pozitia in ziua t = tanh(semnal_equal_weight_cauzal[t]), folosind doar trecutul.
    Returneaza net_return, sharpe (anualizat ~252), p_value (permutation test),
    si n_days. NU este consiliere de investitii.
    """
    prices = np.asarray(prices, dtype=float)
    signal = equal_weight_signal(features, causal=True)
    position = np.tanh(signal)
    position = np.where(np.isfinite(position), position, 0.0)

    def strategy(past):
        t = len(past) - 1
        return position[t]

    res = walk_forward(prices, strategy, warmup=warmup, cost=cost)

    n = len(prices)
    fwd = prices[warmup + 1:n] / prices[warmup:n - 1] - 1.0
    pos = res["positions"]
    daily = pos * fwd
    sharpe = float(daily.mean() / daily.std(ddof=0) * np.sqrt(252)) \
        if daily.std(ddof=0) > 0 else 0.0
    perm = permutation_test(pos, fwd, n_perm=n_perm, seed=seed)
    return {
        "net_return": res["net_return"],
        "sharpe": sharpe,
        "p_value": perm["p_value"],
        "n_days": res["n_days"],
    }
