"""Estimators for the portfolio lab: shrunk covariance (Ledoit-Wolf) and shrunk mean (James-Stein), annualisation.

numpy only. Inputs are daily returns; `annualize` converts to per-year units (252 trading days)."""

import numpy as np

TRADING_DAYS = 252


def annualize(mu_daily, cov_daily):
    return np.asarray(mu_daily) * TRADING_DAYS, np.asarray(cov_daily) * TRADING_DAYS


def ledoit_wolf(X):
    """Covariance shrunk toward a scaled identity with the Ledoit-Wolf (2004) analytic intensity.
    X: (n_obs, n_assets) daily returns. Returns (matrix, delta in [0, 1])."""
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    Xc = X - X.mean(axis=0)
    S = Xc.T @ Xc / n
    m = np.trace(S) / p
    d2 = np.sum((S - m * np.eye(p)) ** 2) / p
    if d2 <= 0:
        return S, 1.0
    b2 = sum(np.sum((np.outer(x, x) - S) ** 2) for x in Xc) / (n * n * p)
    delta = min(b2, d2) / d2
    return delta * m * np.eye(p) + (1 - delta) * S, float(delta)


def james_stein_mean(mu, cov, n_obs):
    """Jorion (1986) Bayes-Stein: pull noisy sample means toward their cross-sectional average.
    `cov` is the covariance of the returns in the same units as `mu`."""
    mu = np.asarray(mu, dtype=float)
    p = len(mu)
    target = mu.mean()
    d = mu - target
    q = float(d @ np.linalg.solve(np.asarray(cov, dtype=float), d))
    w = (p + 2) / ((p + 2) + n_obs * q) if q > 0 else 1.0
    return (1 - w) * mu + w * target
