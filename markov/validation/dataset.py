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


def forward_realized_vol(close, horizons=(1, 5, 21)):
    """{h: volatilitate realizata pe urmatoarele h bare} = RMS al randamentelor
    zilnice viitoare. Tinta potrivita pentru indicatorii de vol/complexitate
    (intrebarea 'cat de agitata urmeaza piata', nu 'in ce parte'). nan la coada."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = {}
    if n < 2:
        return {h: np.full(n, np.nan) for h in horizons}
    r = close[1:] / close[:-1] - 1.0                  # randamente zilnice, len n-1
    cs = np.concatenate(([0.0], np.cumsum(r * r)))    # len n; cs[k]=sum(r[:k]^2)
    for h in horizons:
        v = np.full(n, np.nan)
        last = (n - 1) - h                            # ultimul t cu fereastra completa
        if last >= 0:
            t = np.arange(0, last + 1)
            v[t] = np.sqrt((cs[t + h] - cs[t]) / h)
        out[h] = v
    return out


@dataclass
class Panel:
    symbols: list
    features: dict   # symbol -> {indicator_name: ndarray}
    close: dict      # symbol -> ndarray
    returns: dict    # symbol -> {h: ndarray}  (tinta: randament SAU vol, dupa caz)


def build_panel(symbols, data_dir, indicators, horizon_tf="1day",
                horizons=(1, 5, 21), target="return"):
    """Citeste cache-ul, resample la horizon_tf, calculeaza features + tinta forward
    per simbol. target: 'return' (randament cu semn) sau 'vol' (volatilitate realizata).
    Ridica DataUnavailable daca un simbol nu e in cache."""
    tgt_fn = forward_realized_vol if target == "vol" else forward_returns
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
        returns[sym] = tgt_fn(c, horizons=horizons)
    return Panel(list(symbols), features, close, returns)
