"""Tests for the Hidden Markov Model regime detector (Step 10).

Instead of a subjective +/-5% threshold, fit a 3-state Gaussian HMM on
daily returns and let the data define the regimes. Hidden states are
mapped to BEAR/SIDEWAYS/BULL by their fitted mean return (lowest mean ->
BEAR, highest -> BULL).
"""

import numpy as np
import pytest

from markov.states import State
from markov.hmm import hmm_states


def _three_regime_prices(seed=0):
    """Build prices with three clearly separated return regimes."""
    rng = np.random.default_rng(seed)
    bear = rng.normal(-0.03, 0.005, 120)
    side = rng.normal(0.0, 0.005, 120)
    bull = rng.normal(0.03, 0.005, 120)
    rets = np.concatenate([bull, bear, side, bull, bear])
    prices = [100.0]
    for r in rets:
        prices.append(prices[-1] * (1 + r))
    return np.array(prices), rets


def test_returns_one_label_per_return():
    prices, rets = _three_regime_prices()
    states = hmm_states(prices, n_states=3, seed=0)
    assert len(states) == len(prices) - 1


def test_labels_are_real_states():
    prices, _ = _three_regime_prices()
    states = hmm_states(prices, n_states=3, seed=0)
    assert set(states) <= {State.BEAR, State.SIDEWAYS, State.BULL}


def test_strong_bull_segment_labelled_bull():
    prices, rets = _three_regime_prices(seed=1)
    states = hmm_states(prices, n_states=3, seed=1)
    # First 120 returns are the strong-bull regime; most should be BULL.
    first_bull = states[:120]
    bull_frac = sum(s == State.BULL for s in first_bull) / len(first_bull)
    assert bull_frac > 0.8


def test_strong_bear_segment_labelled_bear():
    prices, rets = _three_regime_prices(seed=2)
    states = hmm_states(prices, n_states=3, seed=2)
    # Returns 120..240 are the bear regime.
    bear_seg = states[120:240]
    bear_frac = sum(s == State.BEAR for s in bear_seg) / len(bear_seg)
    assert bear_frac > 0.8


def test_rejects_too_short_series():
    prices = np.array([100.0, 101.0, 102.0])
    with pytest.raises(ValueError):
        hmm_states(prices, n_states=3, seed=0)


def test_reproducible_with_seed():
    prices, _ = _three_regime_prices(seed=5)
    a = hmm_states(prices, n_states=3, seed=7)
    b = hmm_states(prices, n_states=3, seed=7)
    assert a == b
