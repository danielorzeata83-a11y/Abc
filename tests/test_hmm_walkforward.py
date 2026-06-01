"""Tests for the walk-forward HMM strategy (out-of-sample step 10).

The HMM is expensive to fit, so we refit periodically on an expanding
window of PAST returns only, then use that fitted model to label and
trade the next block of days. No future data ever enters a decision.
"""

import numpy as np
import pytest

from markov.hmm_walkforward import hmm_walk_forward_positions


def _three_regime_prices(seed=0, reps=3):
    rng = np.random.default_rng(seed)
    blocks = []
    for _ in range(reps):
        blocks.append(rng.normal(0.03, 0.005, 60))   # bull
        blocks.append(rng.normal(-0.03, 0.005, 60))  # bear
        blocks.append(rng.normal(0.0, 0.005, 60))    # sideways
    rets = np.concatenate(blocks)
    prices = [100.0]
    for r in rets:
        prices.append(prices[-1] * (1 + r))
    return np.array(prices)


def test_returns_positions_and_index_aligned():
    prices = _three_regime_prices()
    pos, start = hmm_walk_forward_positions(
        prices, warmup=120, refit_every=60, seed=0
    )
    # One position per traded day from `start` to second-last price.
    assert len(pos) == (len(prices) - 1) - start
    assert start >= 120


def test_positions_in_unit_range():
    prices = _three_regime_prices(seed=1)
    pos, _ = hmm_walk_forward_positions(
        prices, warmup=120, refit_every=60, seed=1
    )
    assert np.all(pos >= -1.0) and np.all(pos <= 1.0)


def test_no_lookahead_refit_uses_only_past():
    # Spy: record the largest return-index the fitter is ever shown.
    prices = _three_regime_prices(seed=2)
    seen = []

    def spy_fit(past_returns):
        seen.append(len(past_returns))
        # trivial labeller: everything sideways -> flat signal
        from markov.states import State
        return lambda r: State.SIDEWAYS, np.full((3, 3), 1 / 3)

    hmm_walk_forward_positions(
        prices, warmup=120, refit_every=60, seed=2, _fit_fn=spy_fit
    )
    # Every fit must see strictly fewer returns than the full series.
    assert max(seen) < len(prices) - 1
    assert seen == sorted(seen)  # expanding


def test_rejects_warmup_too_large():
    prices = _three_regime_prices()
    with pytest.raises(ValueError):
        hmm_walk_forward_positions(prices, warmup=10_000, refit_every=60)
