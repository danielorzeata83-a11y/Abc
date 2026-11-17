"""Strat de adaptare TIER 2: familia de factori time-series a proiectului (trend,
reversal, vol-managed, low-vol, calendar) ca serii cauzale aliniate la bare, cu
aceeasi semnatura `nume -> callable(Bars) -> ndarray 1D` ca TIER 1. Acestia sunt
"ceilalti indicatori" deja construiti (vezi SIGNAL_ENGINE_PLAN.md / results/REPORT.md),
trecuti acum prin acelasi motor A->E ca microstructura din TIER 1.

Nota: Spearman IC e pe ranguri, deci orice transformare monotona da acelasi IC.
De aceea folosim direct valoarea bruta a factorului (fara clip/scalare la [-1,1]),
iar vol_managed (1/vol) si low_vol (-vol) raman distincte doar prin fereastra.
Motorul ramane agnostic. NU este consiliere de investitii.
"""

import numpy as np
import pandas as pd

from markov.seasonality import turn_of_month_mask

_W_MA = 50        # fereastra trendului (MA50, cel mai puternic edge din REPORT.md)
_W_REV = 5        # lookback reversal pe termen scurt
_W_VOL = 20       # vol-managed: volatilitate pe termen scurt
_W_LOWVOL = 60    # low-vol: volatilitate pe termen lung
_ANN = np.sqrt(252)


def _ret(close):
    c = np.asarray(close, dtype=float)
    r = np.full(len(c), np.nan)
    r[1:] = c[1:] / c[:-1] - 1.0
    return r


def _roll(series, window, fn):
    """fn ('mean'/'std') pe ferestre CAUZALE de lungime `window` (min_periods=window):
    valoarea la t foloseste doar bare pana la t inclusiv -> fara look-ahead."""
    r = pd.Series(np.asarray(series, dtype=float)).rolling(window, min_periods=window)
    return getattr(r, fn)().to_numpy()


def ts_momentum(bars, window=_W_MA):
    """Trend: close[t] / media(close, window)[t] - 1. >0 = pret peste medie (sus)."""
    c = np.asarray(bars.close, dtype=float)
    return c / _roll(c, window, "mean") - 1.0


def ts_reversal(bars, lookback=_W_REV):
    """Mean-reversion: -randamentul recent pe `lookback` bare, scalat la vol.
    Cadere recenta -> pozitiv (asteptam revenire in sus)."""
    c = np.asarray(bars.close, dtype=float)
    n = len(c)
    recent = np.full(n, np.nan)
    recent[lookback:] = c[lookback:] / c[:-lookback] - 1.0
    vol = _roll(_ret(c), lookback, "std")
    with np.errstate(invalid="ignore", divide="ignore"):
        return -recent / (vol * np.sqrt(lookback))


def vol_managed(bars, window=_W_VOL):
    """Vol-managed: invers volatilitatii anualizate pe termen scurt (calm = scor mare)."""
    vol = _roll(_ret(bars.close), window, "std") * _ANN
    with np.errstate(invalid="ignore", divide="ignore"):
        return 1.0 / vol


def low_vol(bars, window=_W_LOWVOL):
    """Anomalie low-vol: -volatilitatea anualizata pe termen lung (mai calm -> scor mai mare)."""
    return -_roll(_ret(bars.close), window, "std") * _ANN


def turn_of_month(bars, n_end=3, n_start=3):
    """Calendar: 1.0 in zilele de cotitura a lunii (ultimele/primele n), altfel 0.0."""
    mask = turn_of_month_mask(np.asarray(bars.timestamps), n_end=n_end, n_start=n_start)
    return mask.astype(float)


INDICATORS = {
    "ts_momentum":   ts_momentum,
    "ts_reversal":   ts_reversal,
    "vol_managed":   vol_managed,
    "low_vol":       low_vol,
    "turn_of_month": turn_of_month,
}
