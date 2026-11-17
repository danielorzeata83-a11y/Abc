"""Scor comun pentru o serie de pozitii cauzale: randament net de costuri pe
turnover, Sharpe anualizat, max drawdown, nr. trade-uri si p-value prin
permutare. Folosit de toate harness-urile (SMC, trend-pullback) ca sa nu
duplicam matematica de evaluare. NU consiliere de investitii.
"""

import numpy as np

from markov.significance import permutation_test


def score_positions(positions, fwd, cost=0.0005, periods_per_year=252,
                    n_perm=1000, seed=0):
    """positions[t] = pozitia tinuta peste fwd[t] (randamentul forward al barei t).

    Sharpe e calculat pe randamentul BRUT (timing pur), anualizat cu
    sqrt(periods_per_year). net_return/max_drawdown sunt NET de cost*turnover.
    p_value vine din testul de permutare (timing real vs noroc).
    """
    positions = np.asarray(positions, dtype=float)
    fwd = np.asarray(fwd, dtype=float)
    daily = positions * fwd
    turnover = np.abs(np.diff(np.concatenate([[0.0], positions])))
    net_daily = daily - cost * turnover

    sd = daily.std(ddof=0)
    sharpe = (float(daily.mean() / sd * np.sqrt(periods_per_year))
              if sd > 0 else float("nan"))
    eq = np.cumprod(1.0 + net_daily)
    peak = np.maximum.accumulate(eq)
    mdd = float((eq / peak - 1.0).min()) if len(eq) else float("nan")
    perm = permutation_test(positions, fwd, n_perm=n_perm, seed=seed)
    return {
        "gross_return": float(np.prod(1.0 + daily) - 1.0),
        "net_return": float(np.prod(1.0 + net_daily) - 1.0),
        "sharpe": sharpe,
        "max_drawdown": mdd,
        "n_trades": int((turnover > 0).sum()),
        "n_days": int(len(positions)),
        "p_value": perm["p_value"],
    }
