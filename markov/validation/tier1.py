"""Strat de adaptare: uniformizeaza cei 13 indicatori TIER 1 (semnaturi heterogene)
intr-un dict `nume -> callable(Bars) -> ndarray 1D` aliniat la bare. jump_component
e despicat in 'jump' si 'jump_ratio'. Default-uri potrivite pentru daily.
Motorul ramane agnostic: cunoaste doar 'nume -> serie'. NU consiliere de investitii.
"""

import numpy as np

from markov.intraday import indicators as I

_W = 20
_W_HURST = 100
_W_RQA = 100
_LOOKBACK_52W = 126
_W_MAX = 21


def _ret(bars):
    c = np.asarray(bars.close, dtype=float)
    r = np.full(len(c), np.nan)
    r[1:] = c[1:] / c[:-1] - 1.0
    return r


def _rqa_eps(bars):
    c = np.asarray(bars.close, dtype=float)
    s = np.nanstd(c)
    return 0.1 * s if s > 0 else 1e-6


INDICATORS = {
    "garman_klass":    lambda b: I.garman_klass(b.open, b.high, b.low, b.close, _W),
    "rogers_satchell": lambda b: I.rogers_satchell(b.open, b.high, b.low, b.close, _W),
    "realized_var":    lambda b: I.realized_variance(b.close, _W),
    "bipower_var":     lambda b: I.bipower_variation(b.close, _W),
    "jump":            lambda b: I.jump_component(b.close, _W)[0],
    "jump_ratio":      lambda b: I.jump_component(b.close, _W)[1],
    "hurst":           lambda b: I.hurst(b.close, _W_HURST),
    "fdi":             lambda b: I.fdi(b.close, _W_HURST),
    "perm_entropy":    lambda b: I.permutation_entropy(b.close, 3, _W),
    "rqa_det":         lambda b: I.rqa_determinism(b.close, _W_RQA, _rqa_eps(b)),
    "corwin_schultz":  lambda b: I.corwin_schultz(b.high, b.low),
    "roll_measure":    lambda b: I.roll_measure(b.close, _W),
    "high_52w_prox":   lambda b: I.high_52w_proximity(b.close, _LOOKBACK_52W),
    "max_effect":      lambda b: I.max_effect(_ret(b), _W_MAX),
}
