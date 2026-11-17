"""Selectie walk-forward GENERICA de parametru: dat un constructor de pozitii
`positions_fn(bars, value) -> positions`, alege valoarea pe felia IN-SAMPLE
(dupa Sharpe) si raporteaza OUT-OF-SAMPLE. Folosit de orice sistem (dip-buy,
trend-pullback) ca sa nu duplicam protectia anti-overfit. NU consiliere de
investitii.
"""

import numpy as np

from markov.posscore import score_positions


def select_param(positions_fn, bars, grid, split=0.5, cost=0.0005,
                 periods_per_year=252, n_perm=1000, seed=0):
    """Alege param pe in-sample (Sharpe), raporteaza in_sample + oos + split_idx."""
    close = np.asarray(bars.close, dtype=float)
    fwd = close[1:] / close[:-1] - 1.0
    cut = int(len(fwd) * split)
    chosen, best = grid[0], -np.inf
    for v in grid:
        pos = positions_fn(bars, v)[:-1]
        ism = score_positions(pos[:cut], fwd[:cut], cost=cost,
                              periods_per_year=periods_per_year, n_perm=1)
        key = ism["sharpe"] if np.isfinite(ism["sharpe"]) else -np.inf
        if key > best:
            chosen, best = v, key
    pos = positions_fn(bars, chosen)[:-1]
    return {
        "chosen": chosen, "split_idx": cut,
        "in_sample": score_positions(pos[:cut], fwd[:cut], cost=cost,
                                     periods_per_year=periods_per_year,
                                     n_perm=n_perm, seed=seed),
        "oos": score_positions(pos[cut:], fwd[cut:], cost=cost,
                               periods_per_year=periods_per_year,
                               n_perm=n_perm, seed=seed),
    }


def oos_streams(positions_fn, bars, grid, split=0.5, cost=0.0005,
                periods_per_year=252):
    """(chosen, positions_oos, fwd_oos) pentru param ales pe in-sample."""
    res = select_param(positions_fn, bars, grid, split=split, cost=cost,
                       periods_per_year=periods_per_year, n_perm=1)
    chosen, cut = res["chosen"], res["split_idx"]
    close = np.asarray(bars.close, dtype=float)
    fwd = close[1:] / close[:-1] - 1.0
    pos = positions_fn(bars, chosen)[:-1]
    return chosen, pos[cut:], fwd[cut:]
