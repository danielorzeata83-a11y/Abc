import numpy as np
import pytest

from sensa.lab_estimators import annualize, james_stein_mean, ledoit_wolf
from sensa.lab_solvers import cvar, project_capped_simplex, solve_cvar, solve_portfolio


def test_projection_gives_nonnegative_weights_summing_to_one_within_the_cap():
    rng = np.random.default_rng(0)
    for cap in (1.0, 0.4, 0.25):
        for _ in range(50):
            w = project_capped_simplex(rng.normal(size=6) * 3, cap)
            assert w.min() >= -1e-12 and w.max() <= cap + 1e-9 and abs(w.sum() - 1) < 1e-9


def test_projection_of_a_feasible_point_is_itself_and_an_infeasible_cap_is_rejected():
    w = np.array([0.5, 0.3, 0.2])
    assert np.allclose(project_capped_simplex(w, 1.0), w)
    with pytest.raises(ValueError):
        project_capped_simplex(np.zeros(3), 0.3)               # 3 * 0.3 < 1: no feasible portfolio


def test_diagonal_covariance_has_a_closed_form_solution_the_solver_must_hit():
    mu = np.array([0.10, 0.08, 0.06, 0.04])
    var = np.array([0.04, 0.03, 0.02, 0.05])
    lam = 3.0
    # w_i = clip((mu_i - nu) / (lam * var_i), 0, 1) with nu chosen so that sum w = 1
    lo, hi = -10.0, 10.0
    for _ in range(200):
        nu = (lo + hi) / 2
        s = np.clip((mu - nu) / (lam * var), 0, 1).sum()
        lo, hi = (nu, hi) if s > 1 else (lo, nu)
    exact = np.clip((mu - nu) / (lam * var), 0, 1)
    for method in ("pgd", "fista"):
        r = solve_portfolio(mu, np.diag(var), lam, method=method, iters=5000)
        assert np.allclose(r["weights"], exact, atol=2e-3), method


def test_fista_needs_fewer_iterations_than_plain_proximal_gradient_for_the_same_accuracy():
    rng = np.random.default_rng(1)
    Q, _ = np.linalg.qr(rng.normal(size=(8, 8)))
    Sigma = Q @ np.diag(np.geomspace(1e-3, 1.0, 8)) @ Q.T          # badly conditioned, like real covariances
    mu = rng.normal(0.08, 0.05, 8)
    slow = solve_portfolio(mu, Sigma, 5.0, method="pgd", iters=20000, tol=1e-10)
    fast = solve_portfolio(mu, Sigma, 5.0, method="fista", iters=20000, tol=1e-10)
    assert np.allclose(slow["weights"], fast["weights"], atol=1e-3) and fast["iterations"] < slow["iterations"]


def test_turnover_penalty_keeps_weights_closer_to_the_previous_portfolio():
    mu = np.array([0.12, 0.05, 0.05])
    Sigma = np.diag([0.04, 0.04, 0.04])
    prev = np.array([0.2, 0.4, 0.4])
    free = solve_portfolio(mu, Sigma, 3.0, w_prev=prev, kappa=0.0, iters=5000)["weights"]
    sticky = solve_portfolio(mu, Sigma, 3.0, w_prev=prev, kappa=0.05, iters=5000)["weights"]
    assert np.abs(sticky - prev).sum() < np.abs(free - prev).sum()
    huge = solve_portfolio(mu, Sigma, 3.0, w_prev=prev, kappa=10.0, iters=5000)["weights"]
    assert np.allclose(huge, prev, atol=5e-3)


def test_cap_limits_the_largest_weight():
    mu = np.array([0.30, 0.01, 0.01, 0.01])
    w = solve_portfolio(mu, np.eye(4) * 0.04, 1.0, cap=0.4, iters=3000)["weights"]
    assert w.max() <= 0.4 + 1e-6 and abs(w.sum() - 1) < 1e-9


def test_cvar_of_a_known_sample():
    r = np.arange(-9, 11, dtype=float).reshape(-1, 1) / 100          # 20 returns: -9% .. +10%
    assert cvar(np.array([1.0]), r, alpha=0.9) == pytest.approx(0.085)    # mean loss of the worst 2 of 20 (-9%, -8%)


def test_cvar_solution_has_a_lower_tail_loss_than_the_equal_weight_portfolio():
    rng = np.random.default_rng(3)
    calm = rng.normal(0.0004, 0.006, size=(1500, 1))
    crash = rng.normal(0.0006, 0.006, size=(1500, 1)) - (rng.random((1500, 1)) < 0.03) * 0.08      # fat left tail
    R = np.hstack([calm, crash, rng.normal(0.0003, 0.008, size=(1500, 1))])
    mu = R.mean(axis=0) * 252
    eq = np.ones(3) / 3
    w = solve_cvar(mu, R, lam=20.0, alpha=0.95, iters=3000)["weights"]
    assert cvar(w, R, 0.95) < cvar(eq, R, 0.95) and abs(w.sum() - 1) < 1e-9 and w[1] < eq[1]


def test_ledoit_wolf_returns_a_symmetric_positive_definite_shrunk_matrix_and_a_coefficient_in_unit_range():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(60, 10)) * 0.01
    S, delta = ledoit_wolf(X)
    assert 0 <= delta <= 1 and np.allclose(S, S.T) and np.linalg.eigvalsh(S).min() > 0
    X_big = rng.normal(size=(20000, 3)) * np.array([0.005, 0.01, 0.02])          # unequal volatilities: identity is a poor target
    assert ledoit_wolf(X_big)[1] < 0.01                    # lots of data: almost no shrinkage


def test_james_stein_pulls_noisy_means_toward_their_average_and_annualize_scales_by_252():
    mu = np.array([0.30, -0.20, 0.05, 0.0])
    S = np.eye(4) * 0.04
    shrunk = james_stein_mean(mu, S, n_obs=250)
    assert np.ptp(shrunk) < np.ptp(mu) and shrunk.mean() == pytest.approx(mu.mean(), abs=1e-9)
    m, c = annualize(np.array([0.001]), np.array([[0.0001]]))
    assert m[0] == pytest.approx(0.252) and c[0, 0] == pytest.approx(0.0252)
