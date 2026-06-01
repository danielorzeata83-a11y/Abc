"""Walk-forward HMM strategy with no look-ahead (out-of-sample step 10).

A full daily HMM refit over thousands of days is too slow, so we refit on
an expanding window of PAST returns every `refit_every` days. Between
refits we reuse the most recent fitted model to (a) decide today's state
from the past returns and (b) read the signal off the transition matrix
estimated on those past labels. No future return ever influences a
position.
"""

import numpy as np

from markov.states import State, daily_returns
from markov.transition import transition_matrix
from markov.signal import position_signal


def _default_fit(past_returns, n_states=3, seed=None, n_iter=50, n_restarts=5):
    """Fit a Gaussian HMM on past returns; return (labeller, matrix).

    labeller(returns_array) -> State for the last day of that array.
    matrix is the transition matrix estimated on the past labels.
    """
    from hmmlearn import hmm

    X = past_returns.reshape(-1, 1)
    base = np.random.default_rng(seed)
    best, best_score = None, -np.inf
    for _ in range(n_restarts):
        rs = int(base.integers(0, 2**31 - 1))
        m = hmm.GaussianHMM(
            n_components=n_states, covariance_type="diag",
            n_iter=n_iter, random_state=rs,
        )
        try:
            m.fit(X)
            s = m.score(X)
        except Exception:
            continue
        if s > best_score:
            best, best_score = m, s
    if best is None:
        raise RuntimeError("HMM failed to fit")

    means = best.means_.flatten()
    order = np.argsort(means)
    label_for = {order[0]: State.BEAR, order[1]: State.SIDEWAYS,
                 order[2]: State.BULL}

    past_labels = [label_for[h] for h in best.predict(X)]
    P = transition_matrix(past_labels)

    def labeller(returns_array):
        h = best.predict(returns_array.reshape(-1, 1))
        return label_for[h[-1]]

    return labeller, P


def hmm_walk_forward_positions(prices, warmup=250, refit_every=60,
                               seed=None, _fit_fn=None):
    """Generate out-of-sample HMM positions via periodic refits.

    Returns (positions, start_index) where positions[k] is the target
    position for price-day (start_index + k), earning the return realised
    over the following day.
    """
    prices = np.asarray(prices, dtype=float)
    returns = daily_returns(prices)
    n = len(returns)
    if warmup >= n - 1:
        raise ValueError(f"warmup={warmup} too large for {n} returns")

    fit_fn = _fit_fn if _fit_fn is not None else _default_fit

    positions = []
    labeller = None
    P = None
    for t in range(warmup, n):
        # Refit on past returns only (returns[:t]) at each refit boundary.
        if (t - warmup) % refit_every == 0 or labeller is None:
            if _fit_fn is not None:
                labeller, P = fit_fn(returns[:t])
            else:
                labeller, P = fit_fn(returns[:t], seed=seed)

        today_state = labeller(returns[:t])  # past-only labelling
        if today_state == State.UNKNOWN:
            positions.append(0.0)
        else:
            positions.append(position_signal(P, today_state))

    return np.array(positions), warmup
