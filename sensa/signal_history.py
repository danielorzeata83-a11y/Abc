"""Point-in-time samples for testing the picks signals in the past.

Fund signals come from each quarter's own 13F overview (known once the funds filed); price signals use only closes up to
the signal date; insider signals use only trades already *filed* in the 30 days before the date. Forward returns start at
the first close on or after the date. Nothing from after a date can reach that date's sample."""

import bisect
import math

import numpy as np
import pandas as pd

from sensa.signal_research import ForwardReturns, evaluate_signal, evidence_weights, verdict
from sensa.picks_signals import insider_features, momentum_features, smart_money_features, zscores

MAPPING = {"smart_money": "smart", "momentum_12_1": "momentum", "trend": "trend", "quality_sharpe": "quality", "insider_net": "insider"}
LABELS = {"smart_money": "Top funds buying (holder count + active flow)", "holders_change": "Change in number of top funds holding",
          "active_flow": "Active net buying by top funds", "net_new": "Funds opening minus closing positions", "momentum_12_1": "Price momentum (12 months, last month excluded)",
          "trend": "Above the 200-day average", "quality_sharpe": "Risk-adjusted return (1-year Sharpe)", "insider_net": "Insider net buying (filed in the last 30 days)"}


def _pit_closes(closes_fn, ticker, day):
    h = closes_fn(ticker)
    if not h:
        return None
    i = bisect.bisect_right(h[0], day)
    return h[1][:i]


def _universe(ov, min_holders, max_names=200):
    rows = [s for s in ov["stocks"] if s["kind"] in ("stock", "adr") and not s.get("gone") and not s.get("new_listing")
            and s["holders"] >= min_holders and s.get("ticker")]
    return sorted(rows, key=lambda s: (s["holders"], s["value"]), reverse=True)[:max_names]


def _insider_score(f):
    return float(np.sign(f["net"]) * math.log1p(abs(f["net"]) / 1e5) + 0.5 * f["buyers"]) if f else 0.0


def build_samples(overviews, insider_trades, closes_fn, horizons=(21, 63), min_holders=10, extra_days=90, max_names=200):
    fr = ForwardReturns(closes_fn)
    ovs = sorted(overviews, key=lambda o: o["signal_date"])
    keys = ("smart_money", "holders_change", "active_flow", "net_new", "momentum_12_1", "trend", "quality_sharpe", "insider_net")
    out = {k: {} for k in keys}
    if not ovs:
        return out

    def rows(universe, day, values):
        return [{"ticker": t, "value": v, "fwd": {h: fr.ret(t, day, h) for h in horizons}} for t, v in values.items() if v is not None]
    quarterly = [o["signal_date"] for o in ovs]
    for ov in ovs:
        day = ov["signal_date"]
        uni = _universe(ov, min_holders, max_names)
        feats = {s["ticker"]: smart_money_features(s) for s in uni}
        hz, fz = zscores({t: f["holders_change"] for t, f in feats.items()}), zscores({t: f["flow"] for t, f in feats.items()})
        out["holders_change"][day] = rows(uni, day, {t: f["holders_change"] for t, f in feats.items()})
        out["active_flow"][day] = rows(uni, day, {t: f["flow"] for t, f in feats.items()})
        out["net_new"][day] = rows(uni, day, {t: float(f["net_new"]) for t, f in feats.items()})
        out["smart_money"][day] = rows(uni, day, {t: 0.5 * hz[t] + 0.5 * fz[t] for t in feats})
    start, end = pd.Timestamp(ovs[0]["signal_date"]), pd.Timestamp(ovs[-1]["signal_date"]) + pd.Timedelta(days=extra_days)
    monthly = [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end, freq="ME")]
    for day in sorted(set(quarterly) | set(monthly)):
        ov = next((o for o in reversed(ovs) if o["signal_date"] <= day), None)
        if ov is None:
            continue
        uni = _universe(ov, min_holders, max_names)
        mom, trend, qual = {}, {}, {}
        for s in uni:
            c = _pit_closes(closes_fn, s["ticker"], day)
            f = momentum_features(c) if c else None
            if f:
                mom[s["ticker"]], trend[s["ticker"]], qual[s["ticker"]] = f["ret_12_1"], f["trend"], f["sharpe"]
        out["momentum_12_1"][day], out["trend"][day], out["quality_sharpe"][day] = rows(uni, day, mom), rows(uni, day, trend), rows(uni, day, qual)
        lo = (pd.Timestamp(day) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        recent = [t for t in insider_trades if lo <= t["filed"] <= day]
        feats = insider_features(recent)
        out["insider_net"][day] = rows(uni, day, {s["ticker"]: _insider_score(feats.get(s["ticker"])) for s in uni})
    return out


def summarize_evidence(samples, horizons=(21, 63), defaults=None):
    signals, evidence = {}, {}
    for key, by_date in samples.items():
        stats = evaluate_signal(by_date, horizons=horizons)
        h = max(horizons) if stats[max(horizons)]["n_dates"] >= 4 else min(horizons)
        v = verdict(stats[h])
        signals[key] = {"label": LABELS.get(key, key), "stats": stats, "verdict": v, "decided_on_days": h, "n_dates": stats[h]["n_dates"]}
        if key in MAPPING:
            evidence[key] = {"verdict": v, "mean_ic": stats[h]["mean_ic"], "ic_t": stats[h]["ic_t"], "n_dates": stats[h]["n_dates"]}
    defaults = defaults or {}
    return {"signals": signals, "n_signal_dates": len(samples.get("smart_money", {})),
            "weights": {"default": dict(defaults), "evidence": evidence_weights(evidence, defaults, MAPPING)},
            "caveats": ["Funds' signals are tested on about two years of quarterly reports: few independent observations, so most verdicts will say 'not proven'.",
                        "The stock universe is today's most widely held names with a ticker today (delisted companies are missing): results are flattered.",
                        "House purchases cannot be tested yet (no point-in-time history); they are tracked forward in the live track record."]}
