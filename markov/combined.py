"""Combined strategies: Markov regime as a defensive risk overlay.

Empirically the Markov method has no standalone edge, but its one real
property is detecting bear regimes -- which is how regime-switching is
actually used in practice: as a gate that cuts exposure on top of a base
strategy, not as an entry signal.

All strategies follow the walk_forward contract:
    strategy(past_prices) -> target position in [-1, 1]
and use past prices only (no look-ahead).
"""

import numpy as np

from markov.states import classify_states, State


def make_buy_hold_strategy():
    """Always fully long."""
    def strategy(past_prices):
        return 1.0
    return strategy


def make_trend_strategy(ma_window=20):
    """Long when price is above its moving average, flat otherwise.

    A classic trend-following filter. Returns 0.0 (flat) until there is
    enough history for the moving average.
    """
    def strategy(past_prices):
        past_prices = np.asarray(past_prices, dtype=float)
        if len(past_prices) < ma_window:
            return 0.0
        ma = past_prices[-ma_window:].mean()
        return 1.0 if past_prices[-1] > ma else 0.0
    return strategy


def make_regime_filtered_strategy(base_strategy, window=20, threshold=0.05,
                                  bear_exposure=0.0):
    """Wrap a base strategy with a Markov bear-regime gate.

    When today's classified state is BEAR, scale the base position by
    `bear_exposure` (0.0 = fully out, 0.5 = halved). In any other regime
    -- or when there is not enough history to classify -- the base
    position passes through unchanged.
    """
    def strategy(past_prices):
        base_pos = base_strategy(past_prices)
        if len(past_prices) < window + 1:
            return base_pos  # not enough history to gate
        states = classify_states(past_prices, window=window,
                                 threshold=threshold)
        today = states[-1]
        if today == State.BEAR:
            return base_pos * bear_exposure
        return base_pos
    return strategy
