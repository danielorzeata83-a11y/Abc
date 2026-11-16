"""Signals behind the automatic picks: price momentum and risk, what the big funds are doing, insider and House
trades. Pure functions; every signal becomes a cross-sectional z-score and the composite is a weighted average over
the signals that exist for a ticker."""

import numpy as np


def momentum_features(closes):
    """12-1 month momentum (skips the last month), last-month return, volatility, 1y Sharpe, trend and drawdown."""
    c = np.asarray(closes, dtype=float)
    if len(c) < 253 or (c <= 0).any():
        return None
    r = c[1:] / c[:-1] - 1
    last = r[-252:]
    sd = float(last.std(ddof=1))
    return {"ret_12_1": float(c[-22] / c[-253] - 1), "ret_1m": float(c[-1] / c[-22] - 1), "vol": sd * np.sqrt(252),
            "sharpe": float(last.mean() / sd * np.sqrt(252)) if sd > 1e-9 else None,
            "trend": 1.0 if c[-1] > c[-200:].mean() else 0.0, "drawdown": float(c[-1] / c[-252:].max() - 1)}


def zscores(values, clip=3.0):
    """{key: z} using the keys with a value; the rest stay None. Outliers are clipped at +-`clip`."""
    xs = np.array([v for v in values.values() if v is not None], dtype=float)
    if len(xs) == 0:
        return {k: None for k in values}
    mu, sd = xs.mean(), xs.std()
    return {k: (None if v is None else (0.0 if sd < 1e-12 else float(np.clip((v - mu) / sd, -clip, clip)))) for k, v in values.items()}


def smart_money_features(row):
    prev = row.get("holders_prev") or 0
    return {"holders_change": (row["holders"] - prev) / prev if prev > 0 else float(row["holders"]),
            "flow": row["active_flow"] / row["value"] if row.get("value") else 0.0,
            "net_new": row.get("new", 0) - row.get("exited", 0)}


def insider_features(trades):
    out = {}
    for t in trades:
        x = out.setdefault(t["symbol"], {"buyers": set(), "net": 0.0})
        if t["side"] == "buy":
            x["buyers"].add(t["owner"])
            x["net"] += t["value"]
        elif not t.get("plan"):                       # a scheduled 10b5-1 sale says little about the insider's view
            x["net"] -= t["value"]
    return {s: {"buyers": len(x["buyers"]), "net": x["net"]} for s, x in out.items()}


def politician_features(trades):
    buy, sell = {}, {}
    for t in trades:
        s = t.get("ticker")
        if not s:
            continue
        if t["type"] == "purchase":
            buy.setdefault(s, set()).add(t["member"])
        elif t["type"] in ("sale", "partial sale"):
            sell.setdefault(s, set()).add(t["member"])
    return {s: {"buyers": len(buy.get(s, ())), "sellers": len(sell.get(s, ())), "net": len(buy.get(s, ())) - len(sell.get(s, ()))}
            for s in set(buy) | set(sell)}


def composite(z, weights, min_signals=1):
    avail = {k: v for k, v in z.items() if v is not None and k in weights}
    if len(avail) < min_signals:
        return None
    w = sum(weights[k] for k in avail)
    return sum(weights[k] * v for k, v in avail.items()) / w
