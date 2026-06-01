"""Hidden Markov Model regime detection (Step 10).

Rather than imposing a subjective +/-5% threshold to define states, fit a
Gaussian HMM on daily returns and let the data discover the regimes. The
fitted hidden states are then mapped to BEAR / SIDEWAYS / BULL by their
mean return: the lowest-mean state is BEAR, the highest is BULL, the
middle is SIDEWAYS.

This removes the last subjective input (the threshold), as described in
the source method. Note: HMM labels are an unsupervised fit and can be
unstable on real, noisy data -- a known caveat we test for downstream.
"""

import numpy as np

from markov.states import State, daily_returns


def hmm_states(prices, n_states=3, seed=None, n_iter=100, n_restarts=10):
    """Label each day's regime via a 3-state Gaussian HMM on returns.

    Returns a list of State values (one per daily return). Requires more
    observations than states.

    HMM fitting is non-convex and prone to bad local optima, so we run
    several random restarts and keep the fit with the highest log-
    likelihood -- standard practice for stability.
    """
    from hmmlearn import hmm

    returns = daily_returns(prices)
    if len(returns) <= n_states:
        raise ValueError(
            f"need more than {n_states} returns, got {len(returns)}"
        )

    X = returns.reshape(-1, 1)
    base = np.random.default_rng(seed)
    best_model = None
    best_score = -np.inf
    for _ in range(n_restarts):
        rs = int(base.integers(0, 2**31 - 1))
        model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type="diag",
            n_iter=n_iter,
            random_state=rs,
        )
        try:
            model.fit(X)
            score = model.score(X)
        except Exception:
            continue
        if score > best_score:
            best_score = score
            best_model = model

    if best_model is None:
        raise RuntimeError("HMM failed to fit on all restarts")
    model = best_model
    hidden = model.predict(X)

    # Map hidden-state index -> State by ascending fitted mean return.
    means = model.means_.flatten()
    order = np.argsort(means)  # lowest mean first
    label_for = {
        order[0]: State.BEAR,
        order[1]: State.SIDEWAYS,
        order[2]: State.BULL,
    }
    return [label_for[h] for h in hidden]
