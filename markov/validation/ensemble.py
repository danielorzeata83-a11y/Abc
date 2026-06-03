"""Ansamblu de indicatori (pasul E). Z-score CAUZAL (doar trecut) pentru a evita
look-ahead-ul; full-sample doar pentru afisare descriptiva. Evaluarea ruleaza prin
backtest.walk_forward + significance.permutation_test. NU este consiliere de investitii.
"""

import numpy as np


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
