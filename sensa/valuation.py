"""Valuation thermometer and the value + quality screener, on the S&P 500 fundamentals snapshot in ci_data/.
Value = how cheap P/E, P/B and P/S are against sector peers; quality = EBITDA margin (return on equity for banks)
against sector peers. Context for judgement, not a buy signal: the snapshot is a point in time and ratios are noisy."""

import math
import os

import pandas as pd

from markov.fundamentals import cheaper_than_pct
from markov.screener import QUADRANTS, compute_scores

_RATIOS = (("P/E", "Price/Earnings"), ("P/B", "Price/Book"), ("P/S", "Price/Sales"))


def _num(v, nd=None):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, nd) if nd is not None else f


def _label(score):
    return None if score is None else "cheap" if score >= 66 else "expensive" if score <= 33 else "fair"


class Valuation:
    def __init__(self, csv_path):
        try:
            self.df = compute_scores(pd.read_csv(csv_path))
        except (OSError, ValueError, KeyError):
            self.df = None

    def screen(self, quadrant=None, limit=80):
        counts = {q: 0 for q in QUADRANTS + ("n/a",)}
        if self.df is None:
            return {"total": 0, "counts": counts, "rows": []}
        df = self.df
        for q, n in df["quadrant"].value_counts().items():
            counts[q] = int(n)
        d = df if not quadrant else df[df["quadrant"] == quadrant]
        d = d.sort_values(["value_pct", "quality_pct"], ascending=False, na_position="last")
        rows = [{"ticker": r["Symbol"], "name": r.get("Name"), "sector": r["Sector"], "pe": _num(r["Price/Earnings"], 1),
                 "pb": _num(r["Price/Book"], 1), "ps": _num(r["Price/Sales"], 1),
                 "ebitda_margin_pct": _num(r["EBITDA Margin"] * 100, 0), "dividend_pct": _num(r["Dividend Yield"] * 100, 1),
                 "value_pct": _num(r["value_pct"], 0), "quality_pct": _num(r["quality_pct"], 0), "quadrant": r["quadrant"]}
                for _, r in d.head(limit).iterrows()]
        return {"total": int(len(df)), "counts": counts, "rows": rows, "shown": len(rows)}

    def thermometer(self, ticker, live_pe=None):
        """0-100 (100 = cheapest) from the P/E, P/B and P/S percentiles against sector peers; the P/E can be replaced
        by a live one. Tickers outside the snapshot only get the P/E against the whole index."""
        if self.df is None:
            return None
        df, t = self.df, ticker.upper()
        hit = df[df["Symbol"] == t]
        live_pe = _num(live_pe)
        if hit.empty:
            if not live_pe or live_pe <= 0:
                return None
            pct = cheaper_than_pct(live_pe, df["Price/Earnings"].to_numpy())
            return {"ticker": t, "in_snapshot": False, "sector": None, "score": _num(pct, 0), "label": _label(_num(pct)),
                    "ratios": [{"name": "P/E", "value": live_pe, "sector_median": None,
                                "market_median": _num(df["Price/Earnings"].median(), 1), "cheaper_than_sector_pct": _num(pct, 0)}],
                    "quality_pct": None, "quadrant": None}
        r = hit.iloc[0]
        peers = df[df["Sector"] == r["Sector"]]
        if len(peers) < 4:
            peers = df
        ratios, pcts = [], []
        for name, col in _RATIOS:
            v = live_pe if name == "P/E" and live_pe and live_pe > 0 else _num(r[col])
            pct = cheaper_than_pct(v, peers[col].to_numpy()) if v is not None else float("nan")
            if math.isfinite(pct):
                pcts.append(pct)
            ratios.append({"name": name, "value": _num(v, 1), "sector_median": _num(peers[col].median(), 1),
                           "market_median": _num(df[col].median(), 1), "cheaper_than_sector_pct": _num(pct, 0)})
        score = sum(pcts) / len(pcts) if pcts else None
        return {"ticker": t, "in_snapshot": True, "sector": r["Sector"], "score": _num(score, 0), "label": _label(score),
                "ratios": ratios, "quality_pct": _num(r["quality_pct"], 0),
                "quadrant": None if r["quadrant"] == "n/a" else r["quadrant"]}


def default_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ci_data", "sp500_financials.csv")
