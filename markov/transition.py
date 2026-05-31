"""Markov transition matrix and multi-step forecasting (Step 3-4, 6-7).

The transition matrix P is a 3x3 stochastic matrix where P[i, j] is the
empirical probability of moving from state i today to state j tomorrow.
Only the three real states (BEAR, SIDEWAYS, BULL) are modelled; UNKNOWN
labels are dropped before counting.
"""

import numpy as np

from markov.states import State

_REAL_STATES = (State.BEAR, State.SIDEWAYS, State.BULL)


def transition_matrix(states):
    """Build a 3x3 row-stochastic transition matrix from a state sequence.

    Rows are indexed by today's state, columns by tomorrow's state, using
    the State IntEnum values (BEAR=0, SIDEWAYS=1, BULL=2). A state with no
    observed outgoing transitions gets a uniform row (1/3 each), the
    maximum-entropy prior in the absence of evidence.
    """
    seq = [s for s in states if s in _REAL_STATES]
    if not seq:
        raise ValueError("state sequence is empty after dropping UNKNOWN")

    counts = np.zeros((3, 3), dtype=float)
    for today, tomorrow in zip(seq[:-1], seq[1:]):
        counts[int(today), int(tomorrow)] += 1.0

    P = np.empty((3, 3), dtype=float)
    row_totals = counts.sum(axis=1)
    for i in range(3):
        if row_totals[i] == 0:
            P[i] = 1.0 / 3.0
        else:
            P[i] = counts[i] / row_totals[i]
    return P


def forecast(P, days):
    """N-day-ahead transition matrix: P raised to the `days` power.

    P^1 is tomorrow, P^2 is two days out, etc. (Step 6: "squaring the
    matrix"). As `days` grows this converges to the stationary
    distribution (Step 7).
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    return np.linalg.matrix_power(P, days)


def stationary_distribution(P, tol=1e-12, max_iter=10_000):
    """Long-run state distribution: the left eigenvector of P for eigenvalue 1.

    Computed by power iteration on a uniform start, which is robust for
    well-behaved (irreducible, aperiodic) chains.
    """
    pi = np.full(3, 1.0 / 3.0)
    for _ in range(max_iter):
        nxt = pi @ P
        if np.max(np.abs(nxt - pi)) < tol:
            return nxt / nxt.sum()
        pi = nxt
    return pi / pi.sum()
