"""Your own portfolio: positions you enter, valued at the last close, with risk, overlap with what the big funds and
insiders do, warnings, and alternative weightings (equal, inverse-volatility, a risk-aware optimisation) with the trades
they imply. Estimates come from one year of daily prices; they are noisy and are shown as such."""

import json
import math
import os
import re
import threading

import numpy as np
import pandas as pd

from sensa.lab_estimators import james_stein_mean, ledoit_wolf
from sensa.lab_solvers import solve_portfolio

_SYM = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}")


def clean_positions(raw, limit=100):
    if not isinstance(raw, list):
        raise ValueError("positions must be a list")
    acc = {}
    for p in raw:
        try:
            t = str(p["ticker"]).strip().upper()
            sh = float(p["shares"])
            cost = None if p.get("cost") in (None, "") else float(p["cost"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("each position needs a ticker and a number of shares") from None
        if not _SYM.fullmatch(t) or not math.isfinite(sh) or sh <= 0 or (cost is not None and (not math.isfinite(cost) or cost < 0)):
            raise ValueError(f"invalid position {t or '?'}: ticker, shares > 0 and cost >= 0 are required")
        a = acc.setdefault(t, {"shares": 0.0, "cost_total": 0.0, "cost_shares": 0.0})
        a["shares"] += sh
        if cost is not None:
            a["cost_total"] += sh * cost
            a["cost_shares"] += sh
    if len(acc) > limit:
        raise ValueError(f"at most {limit} different tickers")
    return [{"ticker": t, "shares": a["shares"], "cost": a["cost_total"] / a["cost_shares"] if a["cost_shares"] else None} for t, a in acc.items()]


def _money(v):
    a = abs(v)
    s = f"${a / 1e9:.1f}B" if a >= 1e9 else f"${a / 1e6:.1f}M" if a >= 1e6 else f"${a / 1e3:.0f}k"
    return ("-" if v < 0 else "") + s


def _metrics(r):
    r = np.asarray(r, dtype=float)
    wealth = np.cumprod(1 + r)
    k = max(1, int(np.ceil(0.05 * len(r))))
    return {"vol_pct": float(r.std(ddof=1) * np.sqrt(252) * 100), "max_drawdown_pct": float((wealth / np.maximum.accumulate(np.maximum(wealth, 1.0)) - 1).min() * 100),
            "cvar95_pct": float(np.sort(-r)[-k:].mean() * 100), "ret_1y_pct": float((wealth[-1] - 1) * 100)}


def analyze(positions, prices, overview=None, insider_trades=(), picks=None, opt_lam=10.0, cap=0.35):
    if not positions:
        return {"message": "Add your positions (ticker, shares and, if you like, your average cost) to see value, risk and warnings.", "positions": [], "warnings": []}
    ov = {s["ticker"]: s for s in (overview or {}).get("stocks", [])}
    rank = {p["ticker"]: p["rank"] for g in ("stocks", "etfs") for p in (picks or {}).get(g, [])}
    ins = {}
    for t in insider_trades:
        if t["side"] == "sell" and not t.get("plan"):
            ins[t["symbol"]] = ins.get(t["symbol"], 0.0) - t["value"]
        elif t["side"] == "buy":
            ins[t["symbol"]] = ins.get(t["symbol"], 0.0) + t["value"]
    rows = []
    for p in positions:
        last = prices.last(p["ticker"])
        row = {"ticker": p["ticker"], "shares": p["shares"], "cost": p["cost"], "price": last[1] if last else None, "value": None, "weight": None,
               "pnl": None, "pnl_pct": None, "note": "" if last else "No price available (not found on Yahoo Finance)",
               "funds": None, "pick_rank": rank.get(p["ticker"]), "insider_net": ins.get(p["ticker"])}
        if last:
            row["value"] = p["shares"] * last[1]
            if p["cost"] is not None:
                row["pnl"] = p["shares"] * (last[1] - p["cost"])
                row["pnl_pct"] = (last[1] / p["cost"] - 1) * 100 if p["cost"] else None
        o = ov.get(p["ticker"])
        if o:
            row["funds"] = {"holders": o["holders"], "change": o["holders"] - (o.get("holders_prev") or 0), "flow": o.get("active_flow", 0.0)}
        rows.append(row)
    priced = [r for r in rows if r["value"]]
    if not priced:
        return {"message": "None of the tickers could be priced. Check the symbols.", "positions": rows, "warnings": []}
    total = sum(r["value"] for r in priced)
    for r in priced:
        r["weight"] = r["value"] / total
    costed = [r for r in priced if r["cost"] is not None]
    totals = {"value": total, "cost": sum(r["shares"] * r["cost"] for r in costed) if costed else None,
              "pnl": sum(r["pnl"] for r in costed) if costed else None, "priced": len(priced), "of": len(rows)}
    if totals["cost"]:
        totals["pnl_pct"] = totals["pnl"] / totals["cost"] * 100

    series, trend = {}, {}
    for r in priced:
        h = prices.closes(r["ticker"])
        if h and len(h[1]) >= 60:
            series[r["ticker"]] = pd.Series(h[1], index=h[0])
            trend[r["ticker"]] = h[1][-1] < float(np.mean(h[1][-200:])) if len(h[1]) >= 200 else False
    names = [r["ticker"] for r in priced if r["ticker"] in series]
    w_cur = np.array([next(x["weight"] for x in priced if x["ticker"] == t) for t in names])
    risk, pairs, alternatives, trades, R = None, [], [], [], None
    warnings = []
    if len(names) >= 1:
        px = pd.DataFrame({t: series[t] for t in names}).dropna()
        R = px.pct_change().dropna().iloc[-252:]
        w_n = w_cur / w_cur.sum()
        rp = R.values @ w_n
        risk = {**_metrics(rp), "effective_n": float(1 / np.sum(w_n ** 2)), "top3_weight_pct": float(np.sort(w_n)[::-1][:3].sum() * 100), "beta": None}
        spy = prices.closes("SPY")
        if spy:
            sr = pd.Series(spy[1], index=spy[0]).pct_change().reindex(R.index).dropna()
            if len(sr) > 60:
                x = pd.Series(rp, index=R.index).reindex(sr.index)
                risk["beta"] = float(np.cov(x, sr)[0, 1] / np.var(sr, ddof=1))
        if len(names) >= 2:
            C = R.corr().values
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    if C[i, j] >= 0.85:
                        pairs.append({"a": names[i], "b": names[j], "corr": float(C[i, j])})
            n = len(names)
            mu = R.values.mean(axis=0) * 252
            S, _ = ledoit_wolf(R.values)
            S = S * 252
            mu_s = james_stein_mean(mu, S, len(R))
            vol = R.values.std(axis=0, ddof=1) * np.sqrt(252)
            inv = (1 / vol) / (1 / vol).sum()
            opt = solve_portfolio(mu_s, S, opt_lam, w_prev=w_n, kappa=0.01, cap=max(cap, 1 / n + 0.01))["weights"]
            for name, w in (("current", w_n), ("equal", np.ones(n) / n), ("inverse_vol", inv), ("optimized", opt)):
                alternatives.append({"name": name, "weights": {t: float(x) for t, x in zip(names, w)}, **_metrics(R.values @ w)})
            trades = [{"ticker": t, "delta_pct": float((opt[i] - w_n[i]) * 100), "delta_value": float((opt[i] - w_n[i]) * total)} for i, t in enumerate(names)]
            trades.sort(key=lambda x: -abs(x["delta_pct"]))

    def warn(kind, t, text, sev="warn"):
        warnings.append({"key": f"pf:{kind}:{t or 'all'}", "ticker": t, "text": text, "severity": sev})
    for r in priced:
        if r["weight"] > 0.30 and len(priced) > 1:
            warn("conc", r["ticker"], f"{r['ticker']} is {r['weight']:.0%} of your portfolio")
        if r["pnl_pct"] is not None and r["pnl_pct"] <= -25:
            warn("loss", r["ticker"], f"{r['ticker']} is {abs(r['pnl_pct']):.0f}% below your cost")
        if trend.get(r["ticker"]):
            warn("trend", r["ticker"], f"{r['ticker']} trades below its 200-day average")
        f = r["funds"]
        if f and f["change"] <= -5 and f["flow"] < 0:
            warn("funds", r["ticker"], f"{r['ticker']}: the top funds are selling ({f['holders']} hold it, {f['change']:+d} vs last quarter)")
        if r["insider_net"] is not None and r["insider_net"] <= -1e6:
            warn("insider", r["ticker"], f"{r['ticker']}: insiders sold {_money(-r['insider_net'])} net in the last 90 days")
    if risk and len(priced) >= 2 and risk["effective_n"] < 3.0:
        warn("diversify", None, f"Your portfolio behaves like only {risk['effective_n']:.1f} equal positions")
    for p in pairs:
        warn("pair", p["a"], f"{p['a']} and {p['b']} move together (correlation {p['corr']:.2f}): they count as one bet")
    return {"positions": rows, "totals": totals, "risk": risk, "correlated_pairs": pairs, "warnings": warnings, "alternatives": alternatives,
            "trades_to_optimized": trades, "as_of": max((prices.last(t)[0] for t in names), default=None),
            "note": "Risk and alternatives use one year of daily prices and are estimates; the optimised mix is shrunk and capped but can still be wrong. Not investment advice."}


class MyPortfolio:
    def __init__(self, path, prices, overview_fn=None, insiders=None, picks_fn=None):
        self.path, self.prices, self.overview_fn, self.insiders, self.picks_fn = path, prices, overview_fn, insiders, picks_fn
        self._lock, self._pos = threading.Lock(), []
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    self._pos = clean_positions(json.load(fh)["positions"])
            except (OSError, ValueError, KeyError):
                self._pos = []

    def positions(self):
        with self._lock:
            return [dict(p) for p in self._pos]

    def set(self, raw):
        pos = clean_positions(raw)
        with self._lock:
            self._pos = pos
            if self.path:
                os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump({"positions": pos}, fh)
                os.replace(tmp, self.path)
        return pos

    def get(self):
        pos = self.positions()
        if not pos:
            return analyze([], self.prices)
        self.prices.warm([p["ticker"] for p in pos] + ["SPY"])

        def safe(fn, default):
            try:
                return fn() if fn else default
            except Exception:                                 # missing optional context must not hide the portfolio
                return default
        trades = safe(lambda: self.insiders.trades_since(90) if self.insiders else [], [])
        return analyze(pos, self.prices, overview=safe(self.overview_fn, None), insider_trades=trades, picks=safe(self.picks_fn, None))

    def alerts(self):
        if not self.positions():
            return None
        a = self.get()
        items = [{"key": w["key"], "text": w["text"], "ticker": w["ticker"], "severity": w["severity"]} for w in a.get("warnings", [])]
        return {"section": "portfolio", "title": "Your portfolio", "items": items} if items else {"section": "portfolio", "title": "Your portfolio", "items": []}
