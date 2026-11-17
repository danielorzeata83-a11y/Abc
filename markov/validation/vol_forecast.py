"""Pasul F: prognoza OOS a volatilitatii realizate (inchide bucla peste IC-ul
descriptiv din [A]). Ansamblu equal-weight CAUZAL al unei echipe de indicatori ->
IC fata de vol realizat forward, plus IC pe holdout (a doua jumatate a esantionului,
pe care semnalul nu o influenteaza). Comparand seturi de indicatori arata parcimonia:
echipa mica heterogena ~ setul complet, si bate un singur indicator.

NU este consiliere de investitii.
"""

import warnings

import numpy as np

from markov.validation.dataset import forward_realized_vol
from markov.validation.ensemble import zscore_causal
from markov.validation.ic import spearman_ic

# Echipa ortogonala sugerata de IC marginal: un estimator de vol + coada + nivel.
VOL_TEAM = ("realized_var", "max_effect", "high_52w_prox")


def evaluate_vol_forecast(features, close, horizon=21, orient=False):
    """IC al prognozei equal-weight (cauzale) fata de vol realizat pe `horizon` bare.

    orient=False: medie simpla a z-score-urilor cauzale.
    orient=True : fiecare indicator e intors dupa semnul IC-ului sau, invatat DOAR pe
        prima jumatate a observatiilor valide (in-sample); astfel indicatorii cu semn
        opus (ex. high_52w_prox) nu mai anuleaza semnalul. `ic_holdout` (a doua
        jumatate) e atunci numarul curat out-of-sample.

    Intoarce {ic, ic_holdout, n}."""
    close = np.asarray(close, dtype=float)
    tgt = forward_realized_vol(close, (horizon,))[horizon]
    zs = {nm: zscore_causal(np.asarray(v, dtype=float)) for nm, v in features.items()}

    if orient:
        for nm, z in zs.items():
            m = np.isfinite(z) & np.isfinite(tgt)
            idx = np.flatnonzero(m)
            sign = 1.0
            if len(idx) >= 8:
                first = idx[: len(idx) // 2]            # in-sample, fara look-ahead
                s = spearman_ic(z[first], tgt[first])
                if np.isfinite(s) and s < 0:
                    sign = -1.0
            zs[nm] = sign * z

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        fc = np.nanmean(np.column_stack([zs[nm] for nm in features]), axis=1)

    m = np.isfinite(fc) & np.isfinite(tgt)
    out = {"ic": spearman_ic(fc[m], tgt[m]), "ic_holdout": float("nan"),
           "n": int(m.sum())}
    idx = np.flatnonzero(m)
    if len(idx) >= 8:
        half = idx[len(idx) // 2:]
        out["ic_holdout"] = spearman_ic(fc[half], tgt[half])
    return out


def pooled_vol_forecast(features_by_sym, close_by_sym, names, horizon=21):
    """Mediaza IC-urile de prognoza pe simboluri (naiv si orientat pe semn)."""
    ics, holds, oris, n = [], [], [], 0
    for s in close_by_sym:
        feats = {nm: features_by_sym[s][nm] for nm in names
                 if nm in features_by_sym[s]}
        if not feats:
            continue
        r = evaluate_vol_forecast(feats, close_by_sym[s], horizon, orient=False)
        ro = evaluate_vol_forecast(feats, close_by_sym[s], horizon, orient=True)
        ics.append(r["ic"]); holds.append(r["ic_holdout"])
        oris.append(ro["ic_holdout"]); n += r["n"]
    fin = lambda a: [x for x in a if np.isfinite(x)]
    mean = lambda a: float(np.mean(fin(a))) if fin(a) else float("nan")
    return {"ic": mean(ics), "ic_holdout": mean(holds),
            "ic_oriented": mean(oris), "n": n}

