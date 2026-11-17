"""Harness SMC (Smart Money Concepts) — codifica MECANIC si CAUZAL o regula
clasica de "smart money": Break of Structure (BOS) + retest intr-un Fair Value
Gap (FVG). Totul fara look-ahead, ca sa testam onest daca SMC are vreun edge
cand NU repainteaza.

Primitive:
- swing_points: varfuri/funduri pivot, confirmate abia dupa k bare (cunoscute
  doar in viitor -> raportate cauzal la t = pivot + k).
- fair_value_gaps: golurile de 3 bare (bullish: low[i] > high[i-2]).
- smc_positions: masina de stari BOS+retest -> pozitie tinta in {-1,0,+1}.
- backtest_smc: scoreaza pozitiile pe randamentele forward, net de costuri pe
  turnover, + Sharpe, max drawdown si p-value prin test de permutare.

ATENTIE: artefact de cercetare descriptiv. NU consiliere de investitii.
"""

import numpy as np

from markov.posscore import score_positions


def swing_points(high, low, k=2):
    """Pivot swing highs/lows raportate CAUZAL.

    Un swing high la bara i (high[i] = maximul ferestrei [i-k, i+k]) e
    cunoscut abia la t = i+k (are nevoie de k bare in viitor). Intoarce
    (sh, sl): valoarea ultimului swing high / low confirmat *cunoscut la t*,
    NaN pana exista unul. Fara repaint: sh[t]/sl[t] folosesc doar date <= t.
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    n = len(high)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    last_h = np.nan
    last_l = np.nan
    for t in range(n):
        i = t - k                       # pivot ce devine confirmabil exact la t
        if i - k >= 0 and i + k < n:
            win_h = high[i - k:i + k + 1]
            win_l = low[i - k:i + k + 1]
            if high[i] == win_h.max():
                last_h = float(high[i])
            if low[i] == win_l.min():
                last_l = float(low[i])
        sh[t] = last_h
        sl[t] = last_l
    return sh, sl


def fair_value_gaps(high, low):
    """Fair Value Gaps (goluri de 3 bare), cunoscute la bara i (fara repaint).

    Bullish: low[i] > high[i-2] -> zona (high[i-2], low[i]) ramane neumpluta.
    Bearish: high[i] < low[i-2]  -> zona (high[i], low[i-2]).
    Intoarce {"bullish": [(i, bottom, top)], "bearish": [(i, bottom, top)]}.
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    bull, bear = [], []
    for i in range(2, len(high)):
        if low[i] > high[i - 2]:
            bull.append((i, float(high[i - 2]), float(low[i])))
        if high[i] < low[i - 2]:
            bear.append((i, float(high[i]), float(low[i - 2])))
    return {"bullish": bull, "bearish": bear}


def smc_positions(bars, k=2, timeout=10):
    """Pozitie tinta in {-1,0,+1} dintr-o regula SMC simpla, complet cauzala:

    1. BOS bullish: close[t] depaseste ultimul swing high confirmat -> structura
       se rupe in sus. (simetric pentru bear)
    2. Dupa BOS, "armeaza" cel mai recent FVG in directia respectiva si asteapta
       un RETEST: pretul revine in gol (low atinge plafonul golului bullish).
    3. La retest intra LONG/SHORT; iese la BOS opus sau la stop (close iese din
       gol). Disarmeaza daca retestul nu vine in `timeout` bare.

    Totul foloseste doar date <= t (swing_points si FVG sunt cunoscute cauzal),
    deci seria de pozitii e prefix-stabila: fara repaint, fara look-ahead.
    """
    high = np.asarray(bars.high, dtype=float)
    low = np.asarray(bars.low, dtype=float)
    close = np.asarray(bars.close, dtype=float)
    n = len(close)
    sh, sl = swing_points(high, low, k)
    fvg = fair_value_gaps(high, low)
    bull_by_idx = {i: (bot, top) for (i, bot, top) in fvg["bullish"]}
    bear_by_idx = {i: (bot, top) for (i, bot, top) in fvg["bearish"]}

    positions = np.zeros(n)
    pos, state, zone, since = 0.0, "FLAT", None, 0
    cur_bull, cur_bear = None, None
    for t in range(n):
        cur_bull = bull_by_idx.get(t, cur_bull)
        cur_bear = bear_by_idx.get(t, cur_bear)
        h, l = sh[t], sl[t]
        bos_bull = (not np.isnan(h)) and close[t] > h
        bos_bear = (not np.isnan(l)) and close[t] < l

        if state == "LONG":
            if bos_bear or (zone is not None and close[t] < zone[0]):
                pos, state, zone = 0.0, "FLAT", None
        elif state == "SHORT":
            if bos_bull or (zone is not None and close[t] > zone[1]):
                pos, state, zone = 0.0, "FLAT", None
        elif state == "ARMED_LONG":
            if bos_bear or (t - since) > timeout:
                state, zone = "FLAT", None
            elif low[t] <= zone[1]:                 # retest in golul bullish
                pos, state = 1.0, "LONG"
        elif state == "ARMED_SHORT":
            if bos_bull or (t - since) > timeout:
                state, zone = "FLAT", None
            elif high[t] >= zone[0]:                # retest in golul bearish
                pos, state = -1.0, "SHORT"

        if state == "FLAT":
            if bos_bull and cur_bull is not None:
                state, zone, since = "ARMED_LONG", cur_bull, t
            elif bos_bear and cur_bear is not None:
                state, zone, since = "ARMED_SHORT", cur_bear, t

        positions[t] = pos
    return positions


def backtest_smc(bars, cost=0.0005, periods_per_year=252, n_perm=1000, seed=0,
                 **kw):
    """Scoreaza regula SMC pe randamentele forward, NET de costuri pe turnover.

    `cost` = cost pe unitate de turnover (0.0005 = 5 bps round-trip). Sharpe e
    anualizat cu sqrt(periods_per_year) (foloseste 252 pe bare zilnice; ajusteaza
    pentru bare intraday). p_value vine din testul de permutare (timing real vs
    noroc). Intoarce gross/net/sharpe/max_drawdown/n_trades/n_days/p_value.

    NU consiliere de investitii — harness de verificare onesta a SMC.
    """
    pos = smc_positions(bars, **kw)
    close = np.asarray(bars.close, dtype=float)
    fwd = close[1:] / close[:-1] - 1.0
    return score_positions(pos[:-1], fwd, cost=cost,
                           periods_per_year=periods_per_year,
                           n_perm=n_perm, seed=seed)
