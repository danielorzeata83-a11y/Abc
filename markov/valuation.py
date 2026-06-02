"""Valuation thermometer from Shiller CAPE (PE10).

CAPE measures how expensive the market is versus its own history; high CAPE
has historically meant low 10-year forward returns (and vice-versa). These
helpers label a reading, rank it against history, and project a forward
return via a simple linear fit. A 10-year signal, useless for short-term
timing. Not investment advice.
"""

import numpy as np


def valuation_label(cape, cheap=15.0, expensive=25.0):
    """CHEAP / NORMAL / EXPENSIVE by CAPE thresholds."""
    if cape < cheap:
        return "CHEAP"
    if cape > expensive:
        return "EXPENSIVE"
    return "NORMAL"


def percentile_rank(value, history):
    """Percent of `history` strictly below `value` (0-100)."""
    history = np.asarray(history, dtype=float)
    return float((history < value).mean() * 100.0)


def implied_forward_return(cape, hist_cape, hist_fwd):
    """Predicted annualised forward return from a linear fit on CAPE."""
    hist_cape = np.asarray(hist_cape, dtype=float)
    hist_fwd = np.asarray(hist_fwd, dtype=float)
    if np.ptp(hist_cape) == 0:
        return float(hist_fwd.mean())
    slope, intercept = np.polyfit(hist_cape, hist_fwd, 1)
    return float(slope * cape + intercept)
