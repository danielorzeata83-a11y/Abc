"""Pasul D: IC condiționat pe regim. Eticheta implicita = prag Hurst (≷0.5);
etichetele sunt INJECTABILE (poti da iesirea hmm_walk_forward_states cand seria
e destul de lunga). NU este consiliere de investitii.
"""

import numpy as np

from markov.intraday.indicators import hurst
from markov.validation.ic import spearman_ic


def hurst_regime(close, window=100):
    """Etichete: 'trend' unde Hurst>0.5, 'meanrev' unde <0.5, 'na' unde NaN."""
    h = hurst(np.asarray(close, dtype=float), window)
    labels = np.full(len(h), "na", dtype=object)
    labels[h > 0.5] = "trend"
    labels[(h <= 0.5) & np.isfinite(h)] = "meanrev"
    return labels


def conditional_ic(signal, fwd_ret, regime_labels):
    """{regim: IC} calculat pe submultimea fiecarui regim ('na' ignorat)."""
    signal = np.asarray(signal, dtype=float)
    fwd_ret = np.asarray(fwd_ret, dtype=float)
    labels = np.asarray(regime_labels, dtype=object)
    out = {}
    for reg in sorted(set(labels.tolist())):
        if reg == "na":
            continue
        m = labels == reg
        out[reg] = spearman_ic(signal[m], fwd_ret[m])
    return out
