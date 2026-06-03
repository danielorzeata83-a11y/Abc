"""Materia prima pentru validare: randamente forward + panel multi-simbol.
Functii pure peste cache-ul 15m (resample la orizont). NU consiliere de investitii.
"""

from dataclasses import dataclass

import numpy as np

from markov.data_providers import DataUnavailable
from markov.intraday.bars import resample
from markov.intraday.cache import read_bars


def forward_returns(close, horizons=(1, 5, 21)):
    """{h: randament la h bare inainte}; nan pentru ultimele h pozitii."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = {}
    for h in horizons:
        r = np.full(n, np.nan)
        if h < n:
            r[: n - h] = close[h:] / close[: n - h] - 1.0
        out[h] = r
    return out
