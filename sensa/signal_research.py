"""Does a signal predict returns? The standard cross-sectional test, on point-in-time data:
at each signal date rank the stocks by the signal, then compare with what they returned over the next 1 and 3 months.

* rank information coefficient (IC): Spearman correlation between signal and forward return, averaged over dates, with a t-statistic;
* top-group edge: average forward return of the top fifth (and the top 10) minus the average of all stocks.
Few dates means weak evidence; the verdict says so instead of guessing."""

import bisect
import math
from datetime import date

import numpy as np
import pandas as pd


def spearman(x, y):
    if len(x) < 3:
        return None
    rx, ry = pd.Series(x, dtype=float).rank().values, pd.Series(y, dtype=float).rank().values
    if rx.std() < 1e-12 or ry.std() < 1e-12:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


class ForwardReturns:
    """Return from the first close on or after `date` to the close `h` trading days later."""
    def __init__(self, closes_fn, max_gap_days=7):
        self.closes_fn, self.max_gap = closes_fn, max_gap_days

    def ret(self, ticker, day, h):
        hist = self.closes_fn(ticker)
        if not hist:
            return None
        dates, closes = hist
        if (date.fromisoformat(dates[0]) - date.fromisoformat(day)).days > self.max_gap:
            return None
        i = bisect.bisect_left(dates, day)
        j = i + h
        if i >= len(dates) or j >= len(dates) or closes[i] <= 0:
            return None
        return closes[j] / closes[i] - 1


def evaluate_signal(samples_by_date, horizons=(21, 63), min_names=20):
    """samples_by_date: {date: [{ticker, value, fwd: {h: return}}]} -> {h: statistics}."""
    out = {}
    for h in horizons:
        ics, q_ex, t10_ex = [], [], []
        for rows in samples_by_date.values():
            r = [x for x in rows if x.get("value") is not None and x["fwd"].get(h) is not None]
            if len(r) < min_names:
                continue
            ic = spearman([x["value"] for x in r], [x["fwd"][h] for x in r])
            if ic is None:
                continue
            ics.append(ic)
            order = sorted(r, key=lambda x: -x["value"])
            avg = float(np.mean([x["fwd"][h] for x in r]))
            k = max(1, math.ceil(len(r) * 0.2))
            q_ex.append((float(np.mean([x["fwd"][h] for x in order[:k]])) - avg) * 100)
            t10_ex.append((float(np.mean([x["fwd"][h] for x in order[:10]])) - avg) * 100)
        n = len(ics)
        sd = float(np.std(ics, ddof=1)) if n > 1 else 0.0
        out[h] = {"n_dates": n, "mean_ic": float(np.mean(ics)) if n else None, "ic_t": float(np.mean(ics) / (sd / math.sqrt(n))) if n > 1 and sd > 1e-12 else None,
                  "ic_hit_pct": float(np.mean([i > 0 for i in ics]) * 100) if n else None,
                  "top_quintile_excess_pct": float(np.mean(q_ex)) if n else None, "top10_excess_pct": float(np.mean(t10_ex)) if n else None}
    return out


def verdict(st):
    if st["n_dates"] < 4:
        return "too_little_data"
    t, ic = st["ic_t"], st["mean_ic"]
    if t is None:
        return "not_proven"
    if ic > 0 and t >= 2 and st["n_dates"] >= 6:
        return "works"
    if ic < 0 and t <= -2:
        return "negative"
    return "not_proven"


def evidence_weights(evidence, defaults, mapping):
    """Scale the default signal weights by what the data showed: negative -> 0, not proven -> half, works -> full (x1.5 if t >= 3);
    untested or too little data -> unchanged. The total weight is preserved."""
    if not evidence:
        return dict(defaults)
    raw = {}
    for key, w in defaults.items():
        ev = next((evidence[s] for s, k in mapping.items() if k == key and s in evidence), None)
        f = 1.0
        if ev:
            f = {"works": 1.5 if (ev.get("ic_t") or 0) >= 3 else 1.0, "not_proven": 0.5, "negative": 0.0}.get(ev["verdict"], 1.0)
        raw[key] = w * f
    total = sum(raw.values())
    scale = sum(defaults.values()) / total if total else 1.0
    return {k: v * scale for k, v in raw.items()}
