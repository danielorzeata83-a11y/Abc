"""Markov strategy adapter for the walk-forward backtest.

Wraps the state classifier, transition matrix, and signal into a single
callable strategy(past_prices) -> position. Everything is computed from
the supplied past prices only, so it is safe to use inside walk_forward.
"""

from markov.states import classify_states, State
from markov.transition import transition_matrix
from markov.signal import position_signal


def make_markov_strategy(window=20, threshold=0.05):
    """Build a strategy(past_prices) -> target position in [-1, 1].

    Returns 0.0 (flat) when there is not enough history to label a state.
    """

    def strategy(past_prices):
        # Need at least `window` returns => window + 1 prices.
        if len(past_prices) < window + 1:
            return 0.0
        states = classify_states(past_prices, window=window, threshold=threshold)
        today = states[-1]
        if today == State.UNKNOWN:
            return 0.0
        P = transition_matrix(states)
        return position_signal(P, today)

    return strategy
