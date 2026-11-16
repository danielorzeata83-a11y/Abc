"""Solvers for the portfolio lab: long-only, fully-invested (optionally capped) weights.

    minimise   -mu.w + (lam/2) w'Sigma w + kappa * sum huber(w - w_prev)      over  {w >= 0, sum w = 1, w <= cap}

Proximal-gradient (`pgd`) and its accelerated variant (`fista`): the smooth part is differentiated, the constraint set
is handled by an exact Euclidean projection (the proximal map of its indicator). The L1 turnover term is smoothed
with a Huber function (width 1e-3, an error of at most kappa * n * 5e-4 in the objective). A CVaR objective is solved
by a projected normalised subgradient method on the scenario returns. numpy only."""

import numpy as np

_EPS = 1e-3


def project_capped_simplex(v, cap=1.0):
    """Euclidean projection onto {w: 0 <= w <= cap, sum w = 1}, exact: w = clip(v - tau, 0, cap) where the piecewise-linear,
    decreasing sum(tau) is interpolated between the breakpoints v_i and v_i - cap."""
    v = np.asarray(v, dtype=float)
    n = len(v)
    if cap * n < 1 - 1e-12:
        raise ValueError("cap too small: no fully-invested portfolio exists")
    taus = np.sort(np.concatenate([v, v - cap]))                     # ascending: sum(tau) decreases along it
    sums = np.clip(v[None, :] - taus[:, None], 0.0, cap).sum(axis=1)
    j = int(np.searchsorted(-sums, -1.0, side="left"))                # first breakpoint where the sum has dropped to <= 1
    if j == 0:
        tau = taus[0] + (sums[0] - 1.0) / max(np.count_nonzero((v - taus[0] > 0) & (v - taus[0] < cap)), 1)
    else:
        t0, t1, s0, s1 = taus[j - 1], taus[j], sums[j - 1], sums[j]
        tau = t0 if s0 == s1 else t0 + (s0 - 1.0) / (s0 - s1) * (t1 - t0)
    w = np.clip(v - tau, 0.0, cap)
    return w / w.sum()


def solve_portfolio(mu, Sigma, lam, w_prev=None, kappa=0.0, cap=1.0, method="fista", iters=2000, tol=1e-9):
    mu, Sigma = np.asarray(mu, dtype=float), np.asarray(Sigma, dtype=float)
    n = len(mu)
    prev = np.ones(n) / n if w_prev is None else np.asarray(w_prev, dtype=float)
    L = lam * float(np.linalg.eigvalsh(Sigma).max()) + (kappa / _EPS if kappa else 0.0)
    L = max(L, 1e-12)

    def grad(w):
        g = -mu + lam * (Sigma @ w)
        if kappa:
            g = g + kappa * np.clip((w - prev) / _EPS, -1.0, 1.0)
        return g

    w = project_capped_simplex(prev, cap)
    y, t, it = w.copy(), 1.0, 0
    for it in range(1, iters + 1):
        w_new = project_capped_simplex(y - grad(y) / L, cap)
        if method == "fista":
            t_new = (1 + np.sqrt(1 + 4 * t * t)) / 2
            y = w_new + ((t - 1) / t_new) * (w_new - w)
            t = t_new
        else:
            y = w_new
        done = np.max(np.abs(w_new - w)) < tol
        w = w_new
        if done:
            break
    return {"weights": w, "iterations": it, "objective": float(-mu @ w + lam / 2 * w @ Sigma @ w
                                                              + (kappa * np.abs(w - prev).sum() if kappa else 0.0))}


def cvar(w, R, alpha=0.95):
    """Expected shortfall of the portfolio loss: mean of the worst (1-alpha) share of -R @ w (a positive number = loss)."""
    losses = -(np.asarray(R, dtype=float) @ np.asarray(w, dtype=float))
    k = max(1, int(np.ceil((1 - alpha) * len(losses) - 1e-9)))
    return float(np.sort(losses)[-k:].mean())


def solve_cvar(mu, R, lam, alpha=0.95, cap=1.0, iters=3000, w_prev=None):
    """minimise -mu.w + lam * sqrt(252) * CVaR_alpha(w) on the capped simplex (R: daily scenario returns, mu: annual)."""
    mu, R = np.asarray(mu, dtype=float), np.asarray(R, dtype=float)
    n = len(mu)
    scale = lam * np.sqrt(252)
    k = max(1, int(np.ceil((1 - alpha) * len(R) - 1e-9)))
    w = project_capped_simplex(np.ones(n) / n if w_prev is None else w_prev, cap)

    def F(x):
        return -mu @ x + scale * cvar(x, R, alpha)
    best, best_f = w.copy(), F(w)
    for t in range(1, iters + 1):
        tail = np.argsort(-(-(R @ w)))[:k]                       # indices of the k worst portfolio days
        g = -mu - scale * R[tail].mean(axis=0)
        norm = np.linalg.norm(g)
        if norm < 1e-14:
            break
        w = project_capped_simplex(w - (0.1 / np.sqrt(t)) * g / norm, cap)
        f = F(w)
        if f < best_f:
            best, best_f = w.copy(), f
    return {"weights": best, "iterations": iters, "objective": float(best_f)}
