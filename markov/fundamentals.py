"""Per-stock valuation CONTEXT from a fundamentals snapshot.

Shows how a stock's valuation ratios compare to its sector and the market
-- relative cheapness as INFORMATION, not a validated buy signal. Per-stock
valuation does not have the index-level CAPE->return evidence; this is
context to inform judgement, not a trade trigger.
"""

import numpy as np
import pandas as pd

RATIOS = ("Price/Earnings", "Price/Book", "Price/Sales")


def cheaper_than_pct(value, peers):
    """Percent of peers MORE expensive (higher ratio) than `value`."""
    peers = np.asarray([p for p in peers if p is not None and np.isfinite(p) and p > 0],
                       dtype=float)
    if len(peers) == 0 or not np.isfinite(value):
        return float("nan")
    return float((peers > value).mean() * 100.0)


def valuation_context(df, ticker, metric="Price/Earnings"):
    """Valuation context for a ticker vs its sector and the market."""
    row = df[df["Symbol"] == ticker]
    if row.empty:
        raise KeyError(f"{ticker} not in fundamentals")
    row = row.iloc[0]
    sector = row["Sector"]
    val = float(row[metric]) if pd.notna(row[metric]) else float("nan")

    sector_peers = df[df["Sector"] == sector][metric].to_numpy()
    sector_pct = cheaper_than_pct(val, sector_peers)
    market_pct = cheaper_than_pct(val, df[metric].to_numpy())

    if np.isnan(sector_pct):
        label = "NORMAL vs sector"
    elif sector_pct >= 66:
        label = "CHEAP vs sector"
    elif sector_pct <= 33:
        label = "EXPENSIVE vs sector"
    else:
        label = "NORMAL vs sector"

    return {
        "ticker": ticker,
        "sector": sector,
        "pe": val,
        "ratios": {r: (float(row[r]) if pd.notna(row[r]) else None) for r in RATIOS},
        "dividend_yield": float(row["Dividend Yield"]) if pd.notna(row["Dividend Yield"]) else None,
        "sector_cheaper_pct": sector_pct,
        "market_cheaper_pct": market_pct,
        "label": label,
    }
