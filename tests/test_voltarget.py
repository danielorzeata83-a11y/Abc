"""Tests for volatility targeting (equal-risk comparison).

Scale a return stream so its trailing realised volatility tracks a
target. Leverage at day t uses only past returns (no look-ahead):
lev[t] = target_vol / trailing_vol(returns[:t]).
"""

import numpy as np
import pytest

from markov.voltarget import vol_target_returns, realised_vol


def test_realised_vol_matches_numpy_std():
    rng = np.random.default_rng(0)
    r = rng.normal(0, 0.02, 500)
    # annualised daily vol
    assert realised_vol(r) == pytest.approx(r.std() * np.sqrt(365))


def test_scaling_brings_vol_near_target():
    rng = np.random.default_rng(1)
    r = rng.normal(0, 0.04, 2000)  # ~76% annual vol
    target = 0.20
    scaled, lev = vol_target_returns(r, target_vol=target, window=60)
    # Measure realised vol of the scaled series over the active region.
    active = scaled[60:]
    out_vol = active.std() * np.sqrt(365)
    assert out_vol == pytest.approx(target, rel=0.35)


def test_no_lookahead_leverage_uses_past_only():
    rng = np.random.default_rng(2)
    r = rng.normal(0, 0.03, 300)
    _, lev = vol_target_returns(r, target_vol=0.2, window=60)
    # First `window` leverages are 0 (insufficient history).
    assert np.all(lev[:60] == 0.0)
    assert np.all(lev[60:] > 0.0)


def test_leverage_is_capped():
    # Very calm series would imply huge leverage; must be capped.
    r = np.full(300, 0.0001)
    _, lev = vol_target_returns(r, target_vol=0.2, window=60, max_leverage=3.0)
    assert np.all(lev <= 3.0)


def test_output_lengths_match_input():
    r = np.random.default_rng(3).normal(0, 0.02, 250)
    scaled, lev = vol_target_returns(r, target_vol=0.2, window=60)
    assert len(scaled) == len(r) == len(lev)


def test_rejects_window_larger_than_series():
    with pytest.raises(ValueError):
        vol_target_returns(np.ones(10), target_vol=0.2, window=60)
