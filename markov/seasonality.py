"""Turn-of-month calendar edge.

Equity returns historically cluster around the turn of the month -- the
last few and first few trading days (Lakonishok & Smidt 1988). Holding the
market only on those days captures much of the return while sitting out
most of the calendar. The schedule is fixed in advance, so there is no
look-ahead, and the low turnover keeps it cost-robust. Its mechanism is
independent of cross-sectional reversal, making it a genuine second edge.
"""

import numpy as np
import pandas as pd


def turn_of_month_mask(dates, n_end=3, n_start=3):
    """Boolean mask: True on the last `n_end` and first `n_start` trading
    days of each calendar month."""
    dates = pd.to_datetime(pd.Series(np.asarray(dates)))
    months = dates.dt.to_period("M").to_numpy()
    idx = np.arange(len(dates))
    mask = np.zeros(len(dates), dtype=bool)
    for _, grp in pd.Series(idx).groupby(months):
        g = grp.to_numpy()
        for j in g[:n_start]:
            mask[j] = True
        for j in g[-n_end:]:
            mask[j] = True
    return mask


def turn_of_month_returns(market_returns, dates, n_end=3, n_start=3):
    """Market return on turn-of-month days, zero (flat) otherwise."""
    market_returns = np.asarray(market_returns, dtype=float)
    if len(market_returns) != len(dates):
        raise ValueError("market_returns and dates must have equal length")
    mask = turn_of_month_mask(dates, n_end=n_end, n_start=n_start)
    return np.where(mask, market_returns, 0.0)
