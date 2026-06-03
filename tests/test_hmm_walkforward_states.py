"""Walk-forward HMM per-day regime labels (no look-ahead)."""

import numpy as np

from markov.states import State
from markov.hmm_walkforward import hmm_walk_forward_states


def test_states_length_and_no_lookahead():
    prices = np.linspace(100.0, 200.0, 60)
    seen = []

    def fake_fit(past):
        seen.append(len(past))                 # records how much history each refit saw

        def labeller(arr):
            return State.BULL if arr[-1] > 0 else State.BEAR
        return labeller, None

    states, start = hmm_walk_forward_states(
        prices, warmup=10, refit_every=5, _fit_fn=fake_fit)

    assert start == 10
    assert len(states) == len(prices) - 1 - 10     # one per return after warmup
    assert all(isinstance(s, State) for s in states)
    # every refit only ever saw past returns (strictly < total returns = 59)
    assert max(seen) < len(prices) - 1
