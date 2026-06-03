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


@dataclass
class Panel:
    symbols: list
    features: dict   # symbol -> {indicator_name: ndarray}
    close: dict      # symbol -> ndarray
    returns: dict    # symbol -> {h: ndarray}


def build_panel(symbols, data_dir, indicators, horizon_tf="1day",
                horizons=(1, 5, 21)):
    """Citeste cache-ul 15m, resample la horizon_tf, calculeaza features + randamente
    forward per simbol. Ridica DataUnavailable daca un simbol nu e in cache."""
    features, close, returns = {}, {}, {}
    for sym in symbols:
        bars15 = read_bars(data_dir, sym)
        if bars15 is None:
            raise DataUnavailable(f"fara cache pentru {sym}")
        bars = resample(bars15, horizon_tf) if horizon_tf != "15m" else bars15
        c = np.asarray(bars.close, dtype=float)
        features[sym] = {name: np.asarray(fn(bars), dtype=float)
                         for name, fn in indicators.items()}
        close[sym] = c
        returns[sym] = forward_returns(c, horizons=horizons)
    return Panel(list(symbols), features, close, returns)
