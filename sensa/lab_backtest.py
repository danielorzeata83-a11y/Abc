"""Walk-forward backtester and performance metrics for the portfolio lab.

At each rebalance day t the strategy sees only the returns of the `window` days before t and returns target
weights; they are held from day t on (weights drift with returns in between) and the cost of the trade
(turnover x bps) is charged on that first day. Nothing in a decision can use the return of the day it earns."""

import numpy as np
import pandas as pd

from sensa.lab_estimators import james_stein_mean, ledoit_wolf
from sensa.lab_solvers import cvar as cvar_of
from sensa.lab_solvers import solve_cvar, solve_portfolio


def walk_forward(R, strategy, window=504, every=21, cost_bps=5.0, start=None, end=None):
    X = R.values
    n_days, n = X.shape
    first = window if start is None else max(start, window)
    last = n_days if end is None else min(end, n_days)
    w, pending = None, 0.0
    rets, drift, rebal_weights, rebal_dates, turnover, costs = [], [], [], [], [], []
    for t in range(first, last):
        if (t - first) % every == 0:
            target = np.asarray(strategy(R.iloc[t - window:t], None if w is None else w.copy()), dtype=float)
            tv = float(target.sum()) if w is None else float(np.abs(target - w).sum())
            pending = tv * cost_bps / 1e4
            w = target
            turnover.append(round(tv, 12))
            costs.append(pending)
            rebal_weights.append(target.copy())
            rebal_dates.append(R.index[t])
        rp = float(w @ X[t])
        rets.append((1 - pending) * (1 + rp) - 1)
        pending = 0.0
        w = w * (1 + X[t]) / (1 + rp)
        drift.append(w.copy())
    idx = R.index[first:last]
    wealth_loss = 1 - float(np.prod([1 - c for c in costs])) if costs else 0.0
    return {"returns": pd.Series(rets, index=idx), "daily_weights": pd.DataFrame(drift, index=idx, columns=R.columns),
            "rebalance_weights": pd.DataFrame(rebal_weights, index=rebal_dates, columns=R.columns),
            "turnover": turnover, "cost_total": wealth_loss}


def metrics(r):
    r = pd.Series(r, dtype=float)
    n = len(r)
    wealth = (1 + r).cumprod()
    total = float(wealth.iloc[-1] - 1)
    ann = float(wealth.iloc[-1] ** (252 / n) - 1)
    sd = float(r.std(ddof=1)) if n > 1 else 0.0
    down = float(np.sqrt(np.mean(np.minimum(r, 0.0) ** 2)))
    dd = float((wealth / wealth.cummax().clip(lower=1.0) - 1).min()) if n else 0.0
    k = max(1, int(np.ceil(0.05 * n - 1e-9)))
    return {"days": n, "total_return": total, "ann_return": ann, "ann_vol": sd * np.sqrt(252),
            "sharpe": float(r.mean() / sd * np.sqrt(252)) if sd > 1e-12 else None,
            "sortino": float(r.mean() / down * np.sqrt(252)) if down > 1e-12 else None,
            "max_drawdown": dd, "calmar": ann / abs(dd) if dd < -1e-12 else None,
            "cvar95": float(np.sort(-r.values)[-k:].mean()) if n else 0.0}


# ----------------------------------------------------------------- strategies (train frame, previous weights) -> weights
def equal_weight(train, w_prev):
    n = train.shape[1]
    return np.ones(n) / n


def _inputs(train, shrink):
    X = train.values
    mu = X.mean(axis=0) * 252
    if shrink:
        S, _ = ledoit_wolf(X)
        S = S * 252
        mu = james_stein_mean(mu, S, len(X))
    else:
        S = np.cov(X.T, ddof=0) * 252
    return mu, S


def make_mean_variance(lam, kappa=0.0, cap=1.0, shrink=True, method="fista", log=None):
    def strat(train, w_prev):
        mu, S = _inputs(train, shrink)
        r = solve_portfolio(mu, S, lam, w_prev=w_prev, kappa=kappa, cap=cap, method=method)
        if log is not None:
            log.append(r["iterations"])
        return r["weights"]
    return strat


def make_cvar(lam, alpha=0.95, cap=1.0, shrink=True, log=None, iters=1500):
    def strat(train, w_prev):
        mu, _ = _inputs(train, shrink)
        r = solve_cvar(mu, train.values, lam, alpha=alpha, cap=cap, w_prev=w_prev, iters=iters)
        if log is not None:
            log.append(r["iterations"])
        return r["weights"]
    return strat
