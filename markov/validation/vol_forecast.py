"""Pasul F: prognoza OOS a volatilitatii realizate (inchide bucla peste IC-ul
descriptiv din [A]). Ansamblu equal-weight CAUZAL al unei echipe de indicatori ->
IC fata de vol realizat forward, plus IC pe holdout (a doua jumatate a esantionului,
pe care semnalul nu o influenteaza). Comparand seturi de indicatori arata parcimonia:
echipa mica heterogena ~ setul complet, si bate un singur indicator.

NU este consiliere de investitii.
"""

import numpy as np

from markov.validation.dataset import forward_realized_vol
from markov.validation.ensemble import equal_weight_signal
from markov.validation.ic import spearman_ic

# Echipa ortogonala sugerata de IC marginal: un estimator de vol + coada + nivel.
VOL_TEAM = ("realized_var", "max_effect", "high_52w_prox")


def evaluate_vol_forecast(features, close, horizon=21):
    """IC al prognozei equal-weight (cauzale) fata de vol realizat pe `horizon` bare.

    Intoarce {ic, ic_holdout, n}. `ic_holdout` = IC pe a doua jumatate a
    observatiilor valide (semnalul e equal-weight, fara fitting, deci IC-ul e deja
    out-of-sample; holdout-ul e un control suplimentar de stabilitate)."""
    fc = equal_weight_signal(features, causal=True)
    tgt = forward_realized_vol(np.asarray(close, dtype=float), (horizon,))[horizon]
    m = np.isfinite(fc) & np.isfinite(tgt)
    out = {"ic": spearman_ic(fc[m], tgt[m]), "ic_holdout": float("nan"),
           "n": int(m.sum())}
    idx = np.flatnonzero(m)
    if len(idx) >= 8:
        half = idx[len(idx) // 2:]
        out["ic_holdout"] = spearman_ic(fc[half], tgt[half])
    return out


def pooled_vol_forecast(features_by_sym, close_by_sym, names, horizon=21):
    """Mediaza IC-urile de prognoza pe simboluri, pentru setul de indicatori `names`."""
    ics, holds, n = [], [], 0
    for s in close_by_sym:
        feats = {nm: features_by_sym[s][nm] for nm in names
                 if nm in features_by_sym[s]}
        if not feats:
            continue
        r = evaluate_vol_forecast(feats, close_by_sym[s], horizon)
        ics.append(r["ic"]); holds.append(r["ic_holdout"]); n += r["n"]
    fin = lambda a: [x for x in a if np.isfinite(x)]
    return {"ic": float(np.mean(fin(ics))) if fin(ics) else float("nan"),
            "ic_holdout": float(np.mean(fin(holds))) if fin(holds) else float("nan"),
            "n": n}
