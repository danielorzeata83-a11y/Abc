"""Evaluare ONESTA a sistemului trend-pullback: il compara cu buy-and-hold pe
ACEEASI felie OOS (avem edge de timing sau doar beta de piata bull?) si ofera
un test de semnificatie AGREGAT pe tot watchlist-ul (un singur test pooled, ca
sa nu cadem in capcana testarii multiple). NU consiliere de investitii.
"""

import numpy as np

from markov.posscore import score_positions
from markov.trendpull import trendpull_positions, walk_forward_select


def bh_metrics(fwd, periods_per_year=252):
    """Buy-and-hold pe randamentele forward date: return, Sharpe, max drawdown."""
    fwd = np.asarray(fwd, dtype=float)
    if len(fwd) == 0:
        return {"bh_return": float("nan"), "bh_sharpe": float("nan"),
                "bh_max_drawdown": float("nan")}
    sd = fwd.std(ddof=0)
    sh = float(fwd.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else float("nan")
    eq = np.cumprod(1.0 + fwd)
    mdd = float((eq / np.maximum.accumulate(eq) - 1.0).min())
    return {"bh_return": float(np.prod(1.0 + fwd) - 1.0), "bh_sharpe": sh,
            "bh_max_drawdown": mdd}


def select_oos_streams(bars, mults=(2.0, 2.5, 3.0, 3.5), split=0.5, cost=0.0005,
                       periods_per_year=252, **rule_kw):
    """Alege mult pe in-sample (ca walk_forward_select) si intoarce seriile OOS:
    (chosen_mult, positions_oos, fwd_oos). positions/fwd au aceeasi lungime."""
    res = walk_forward_select(bars, mults=mults, split=split, cost=cost,
                              periods_per_year=periods_per_year, n_perm=1,
                              **rule_kw)
    chosen, cut = res["chosen_mult"], res["split_idx"]
    close = np.asarray(bars.close, dtype=float)
    fwd = close[1:] / close[:-1] - 1.0
    pos = trendpull_positions(bars, atr_mult=chosen, **rule_kw)[:-1]
    return chosen, pos[cut:], fwd[cut:]


def pooled_significance(streams, cost=0.0005, periods_per_year=252,
                        n_perm=1000, seed=0):
    """Un SINGUR test de timing pe toate seriile OOS concatenate (pos, fwd).
    Raspunde la testarea multipla: nu 10 teste, ci unul pe tot portofoliul."""
    pos = np.concatenate([s[0] for s in streams])
    fwd = np.concatenate([s[1] for s in streams])
    return score_positions(pos, fwd, cost=cost,
                           periods_per_year=periods_per_year,
                           n_perm=n_perm, seed=seed)
