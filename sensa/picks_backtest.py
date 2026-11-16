"""Honest check of the price part of the picks rule: run it month by month in the past with no tuning at all.

Every parameter is fixed in advance (top 10, 12-1 momentum + risk-adjusted return among stocks above their 200-day average,
inverse-volatility weights capped at 20%, 10 bps costs), so the whole period after the warm-up is out of sample. The
smart-money, insider and House signals cannot be tested this way: their historical snapshots were not kept."""

import numpy as np
import pandas as pd

from sensa.lab_backtest import equal_weight, metrics, walk_forward
from sensa.picks import _weights
from sensa.picks_signals import zscores

CAVEAT = ("The universe is today's most widely held stocks, chosen with hindsight (survivorship bias), so the test flatters every "
          "model. Only the price signals are tested; the fund, insider and House signals have no point-in-time history here.")


def make_rank_strategy(top_n=10, max_weight=0.2):
    def strat(train, w_prev):
        X = train.values
        n = X.shape[1]
        cum = np.cumprod(1 + X, axis=0)
        if len(cum) < 253:
            return np.ones(n) / n
        mom = cum[-22] / cum[-253] - 1
        r = X[-252:]
        sd = r.std(axis=0, ddof=1)
        sharpe = np.where(sd > 1e-9, r.mean(axis=0) / np.where(sd > 1e-9, sd, 1) * np.sqrt(252), 0.0)
        trend = cum[-1] > cum[-200:].mean(axis=0)
        ok = np.where(trend)[0]
        if len(ok) == 0:
            return np.ones(n) / n
        zm = zscores({int(i): float(mom[i]) for i in ok})
        zq = zscores({int(i): float(sharpe[i]) for i in ok})
        score = {i: 0.6 * zm[i] + 0.4 * zq[i] for i in zm}
        pick = sorted(score, key=lambda i: -score[i])[:top_n]
        w = np.zeros(n)
        w[pick] = _weights(sd[pick] * np.sqrt(252), max_weight)
        return w
    return strat


def _stats(res):
    m = {k: (v if k == "days" else (None if v is None else float(v))) for k, v in metrics(res["returns"]).items()}
    m["avg_turnover"] = float(np.mean(res["turnover"][1:])) if len(res["turnover"]) > 1 else 0.0
    m["cost_total"] = float(res["cost_total"])
    return m


def rank_backtest(prices, benchmark=None, top_n=10, window=300, every=21, cost_bps=10.0, max_weight=0.2):
    R = prices.pct_change().dropna()
    if len(R) < window + 3 * every:
        raise ValueError(f"not enough history: {len(R)} days for a {window}-day window")
    strat = walk_forward(R, make_rank_strategy(top_n, max_weight), window, every, cost_bps)
    eq = walk_forward(R, equal_weight, window, every, cost_bps)
    daily = {"picks_rule": strat["returns"], "equal_weight": eq["returns"]}
    models = {"picks_rule": _stats(strat), "equal_weight": _stats(eq)}
    idx = strat["returns"].index
    b = benchmark.pct_change().reindex(idx).fillna(0.0) if benchmark is not None else eq["returns"]
    daily["benchmark"] = b
    models["benchmark"] = {k: (v if k == "days" else (None if v is None else float(v))) for k, v in metrics(b).items()} | {"avg_turnover": 0.0, "cost_total": 0.0}
    step = max(1, len(idx) // 250)                                 # at most ~250 chart points
    return {"models": models, "caveat": CAVEAT, "params": {"top_n": top_n, "window": window, "every": every, "cost_bps": cost_bps, "max_weight": max_weight},
            "periods": {"start": idx[0], "end": idx[-1], "days": len(idx), "tickers": len(R.columns)},
            "curves": {"dates": list(idx[::step]), "models": {k: [float(x) for x in (1 + v).cumprod().values[::step]] for k, v in daily.items()}}}
