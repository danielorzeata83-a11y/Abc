"""Sistem TREND-PULLBACK (long-only), codificat MECANIC si CAUZAL:

1. Trend confirmat: close > MA50 SI MA50 in crestere (panta pe `slope_lookback`).
2. Retest: in trend sus, pullback la MA50 (low <= MA50) care inchide inapoi
   deasupra (close > MA50) -> intra long.
3. Iesire: chandelier ATR -- stop = max_high_de_la_intrare - mult*ATR, urca,
   nu coboara niciodata; iesi cand close < stop.

Multiplicatorul `mult` NU se alege din burta: `walk_forward_select` il alege pe
o felie in-sample si raporteaza performanta OUT-OF-SAMPLE. NU consiliere de
investitii -- harness de testare onesta.
"""

import numpy as np
import pandas as pd

from markov.posscore import score_positions


def ma(close, window=50):
    """Media mobila simpla (NaN pe warmup, cauzala)."""
    return pd.Series(np.asarray(close, dtype=float)).rolling(
        window, min_periods=window).mean().to_numpy()


def atr(high, low, close, period=22):
    """Average True Range (medie simpla a True Range pe `period`), cauzal."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low,
                            np.abs(high - prev_close),
                            np.abs(low - prev_close)])
    return pd.Series(tr).rolling(period, min_periods=period).mean().to_numpy()


def trend_up(close, ma_arr, slope_lookback=10):
    """True cand close > MA SI MA e in crestere fata de acum `slope_lookback` zile."""
    close = np.asarray(close, dtype=float)
    ma_arr = np.asarray(ma_arr, dtype=float)
    n = len(close)
    out = np.zeros(n, dtype=bool)
    for t in range(n):
        if t - slope_lookback < 0:
            continue
        m, m_prev = ma_arr[t], ma_arr[t - slope_lookback]
        if np.isnan(m) or np.isnan(m_prev):
            continue
        out[t] = close[t] > m and m > m_prev
    return out


def trendpull_positions(bars, ma_window=50, slope_lookback=10, atr_period=22,
                        atr_mult=3.0):
    """Pozitie long-only {0, +1} din regula trend-pullback, complet cauzala."""
    high = np.asarray(bars.high, dtype=float)
    low = np.asarray(bars.low, dtype=float)
    close = np.asarray(bars.close, dtype=float)
    n = len(close)
    ma_arr = ma(close, ma_window)
    atr_arr = atr(high, low, close, atr_period)
    up = trend_up(close, ma_arr, slope_lookback)

    positions = np.zeros(n)
    pos, state, max_high = 0.0, "FLAT", -np.inf
    for t in range(n):
        start = state
        if start == "LONG":
            max_high = max(max_high, high[t])
            stop = max_high - atr_mult * atr_arr[t]
            if not np.isnan(stop) and close[t] < stop:
                pos, state = 0.0, "FLAT"
        if start == "FLAT":
            if (up[t] and not np.isnan(atr_arr[t])
                    and low[t] <= ma_arr[t] and close[t] > ma_arr[t]):
                pos, state, max_high = 1.0, "LONG", high[t]
        positions[t] = pos
    return positions


def backtest_trendpull(bars, cost=0.0005, periods_per_year=252, n_perm=1000,
                       seed=0, **rule_kw):
    """Scoreaza regula trend-pullback net de costuri (vezi posscore)."""
    pos = trendpull_positions(bars, **rule_kw)
    close = np.asarray(bars.close, dtype=float)
    fwd = close[1:] / close[:-1] - 1.0
    return score_positions(pos[:-1], fwd, cost=cost,
                           periods_per_year=periods_per_year,
                           n_perm=n_perm, seed=seed)


def walk_forward_select(bars, mults=(2.0, 2.5, 3.0, 3.5), split=0.5,
                        cost=0.0005, periods_per_year=252, n_perm=1000, seed=0,
                        **rule_kw):
    """Alege `atr_mult` pe felia IN-SAMPLE (dupa Sharpe) si raporteaza OOS.

    Single holdout: primele `split` din randamente = in-sample (doar pentru
    ALEGERE), restul = out-of-sample (cifra in care ai voie sa crezi). Pozitiile
    se calculeaza pe seria completa (warmup pastrat); doar randamentele se taie.
    """
    close = np.asarray(bars.close, dtype=float)
    fwd = close[1:] / close[:-1] - 1.0
    cut = int(len(fwd) * split)
    chosen, best_key = mults[0], -np.inf
    for m in mults:
        pos = trendpull_positions(bars, atr_mult=m, **rule_kw)[:-1]
        ism = score_positions(pos[:cut], fwd[:cut], cost=cost,
                              periods_per_year=periods_per_year, n_perm=1)
        key = ism["sharpe"] if np.isfinite(ism["sharpe"]) else -np.inf
        if key > best_key:
            chosen, best_key = m, key
    pos = trendpull_positions(bars, atr_mult=chosen, **rule_kw)[:-1]
    return {
        "chosen_mult": chosen,
        "in_sample": score_positions(pos[:cut], fwd[:cut], cost=cost,
                                     periods_per_year=periods_per_year,
                                     n_perm=n_perm, seed=seed),
        "oos": score_positions(pos[cut:], fwd[cut:], cost=cost,
                               periods_per_year=periods_per_year,
                               n_perm=n_perm, seed=seed),
        "split_idx": cut,
    }
