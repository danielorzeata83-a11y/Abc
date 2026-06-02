"""Value + quality screener.

Pure value (cheap ratios) is a trap when the business is deteriorating
("value trap"). This screener scores each stock on VALUE (cheap P/E, P/B,
P/S vs its sector) AND QUALITY (EBITDA margin vs its sector), then assigns
a quadrant. The genuinely useful combination is CHEAP + QUALITY; CHEAP +
LOW QUALITY is the trap to avoid.

Context for judgement, not a validated buy signal. Per-stock valuation
lacks the index-level CAPE->return evidence. Not investment advice.
"""

import numpy as np
import pandas as pd

VALUE_RATIOS = ("Price/Earnings", "Price/Book", "Price/Sales")
QUADRANTS = (
    "CHEAP + QUALITY",
    "CHEAP but LOW QUALITY (trap risk)",
    "QUALITY but PRICEY",
    "EXPENSIVE + LOW QUALITY (avoid)",
)


def _sector_cheaper_pct(df, col):
    """Per-row: % of sector peers MORE expensive (higher ratio) = cheaper-than."""
    def f(g):
        arr = g.to_numpy(dtype=float)
        valid = arr[(arr > 0) & np.isfinite(arr)]
        out = np.full(len(arr), np.nan)
        for i, v in enumerate(arr):
            if v > 0 and np.isfinite(v) and len(valid):
                out[i] = (valid > v).mean() * 100
        return pd.Series(out, index=g.index)
    return df.groupby("Sector")[col].transform(f)


def _sector_better_pct(df, col):
    """Per-row: % of sector peers with LOWER value (higher metric = better)."""
    def f(g):
        arr = g.to_numpy(dtype=float)
        valid = arr[np.isfinite(arr)]
        out = np.full(len(arr), np.nan)
        for i, v in enumerate(arr):
            if np.isfinite(v) and len(valid):
                out[i] = (valid < v).mean() * 100
        return pd.Series(out, index=g.index)
    return df.groupby("Sector")[col].transform(f)


def compute_scores(df):
    """Add Sales, EBITDA Margin, value_pct, quality_pct and quadrant."""
    df = df.copy()
    df["Sales"] = df["Market Cap"] / df["Price/Sales"].replace(0, np.nan)
    df["EBITDA Margin"] = df["EBITDA"] / df["Sales"]

    vpcts = [_sector_cheaper_pct(df, c) for c in VALUE_RATIOS]
    df["value_pct"] = pd.concat(vpcts, axis=1).mean(axis=1)
    df["quality_pct"] = _sector_better_pct(df, "EBITDA Margin")

    def quadrant(row):
        v, q = row["value_pct"], row["quality_pct"]
        if not (np.isfinite(v) and np.isfinite(q)):
            return "n/a"
        if v >= 50 and q >= 50:
            return QUADRANTS[0]
        if v >= 50 and q < 50:
            return QUADRANTS[1]
        if v < 50 and q >= 50:
            return QUADRANTS[2]
        return QUADRANTS[3]

    df["quadrant"] = df.apply(quadrant, axis=1)
    return df
