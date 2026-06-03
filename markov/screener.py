"""Value + quality screener.

Pure value (cheap ratios) is a trap when the business is deteriorating
("value trap"). This screener scores each stock on VALUE (cheap P/E, P/B,
P/S vs its sector) AND QUALITY (EBITDA margin vs its sector), then assigns
a quadrant. The genuinely useful combination is CHEAP + QUALITY; CHEAP +
LOW QUALITY is the trap to avoid.

Context for judgement, not a validated buy signal. Per-stock valuation
lacks the index-level CAPE->return evidence. Not investment advice.
"""

import warnings

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


def _cheaper(value, peers):
    peers = peers[(peers > 0) & np.isfinite(peers)]
    if not (value > 0 and np.isfinite(value)) or len(peers) == 0:
        return np.nan
    return (peers > value).mean() * 100


def _better(value, peers):
    peers = peers[np.isfinite(peers)]
    if not np.isfinite(value) or len(peers) == 0:
        return np.nan
    return (peers < value).mean() * 100


def _ranked(df, col, fn, min_peers):
    """Percentile of each row vs its sector; fall back to the whole market
    when the sector has fewer than `min_peers` members (small/mixed lists)."""
    market = df[col].to_numpy(dtype=float)
    sizes = df.groupby("Sector")[col].transform("count")
    out = np.full(len(df), np.nan)
    for pos, (_, row) in enumerate(df.iterrows()):
        if sizes.iloc[pos] >= min_peers:
            peers = df.loc[df["Sector"] == row["Sector"], col].to_numpy(dtype=float)
        else:
            peers = market  # too few sector peers -> compare to the market
        out[pos] = fn(float(row[col]), peers)
    return out


def _ranked_quality(df, min_peers):
    """Quality percentile, comparing each row only to peers using the SAME
    metric (EBITDA margin vs EBITDA margin, ROE vs ROE) so financials (ROE)
    and the rest (EBITDA margin) are scored apples-to-apples."""
    out = np.full(len(df), np.nan)
    for pos in range(len(df)):
        metric = df["q_metric"].iloc[pos]
        val = float(df["q_value"].iloc[pos])
        same = df[df["q_metric"] == metric]
        sector = same[same["Sector"] == df["Sector"].iloc[pos]]
        peers = (sector if len(sector) >= min_peers else same)["q_value"].to_numpy(float)
        out[pos] = _better(val, peers)
    return out


def compute_scores(df, min_peers=4):
    """Add Sales, EBITDA Margin, value_pct, quality_pct and quadrant.

    Percentiles use sector peers when a sector has >= min_peers members,
    else the whole market (so small or mixed ticker lists stay meaningful).
    """
    df = df.copy().reset_index(drop=True)
    df["Sales"] = df["Market Cap"] / df["Price/Sales"].replace(0, np.nan)
    df["EBITDA Margin"] = df["EBITDA"] / df["Sales"]
    # ROE = earnings/book = (P/B)/(P/E); quality metric for banks etc. with no EBITDA.
    df["ROE"] = df["Price/Book"] / df["Price/Earnings"].replace(0, np.nan)
    use_ebitda = np.isfinite(df["EBITDA Margin"])
    df["q_metric"] = np.where(use_ebitda, "ebitda", "roe")
    df["q_value"] = np.where(use_ebitda, df["EBITDA Margin"], df["ROE"])

    vpcts = [_ranked(df, c, _cheaper, min_peers) for c in VALUE_RATIOS]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        df["value_pct"] = np.nanmean(np.vstack(vpcts), axis=0)
    # A stock with no valid positive P/E has no earnings to be "cheap" against;
    # ranking it on P/B/P/S alone is a value-trap false positive (e.g. firms
    # with negative earnings). Disqualify it from the value score entirely.
    pe = pd.to_numeric(df["Price/Earnings"], errors="coerce").to_numpy(float)
    df.loc[~((pe > 0) & np.isfinite(pe)), "value_pct"] = np.nan
    df["quality_pct"] = _ranked_quality(df, min_peers)

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
