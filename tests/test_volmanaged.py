"""Tests for the vol-managed market edge (Moreira & Muir 2017).

Scale exposure to the market inversely with recent realised variance:
de-risk when volatility spikes, lever up when calm. Improves the market's
risk-adjusted return and cuts drawdowns. A market-DIRECTIONAL timing edge
(carries beta), distinct from market-neutral cross-sectional alphas.

Reuses the tested vol_target_returns engine; this wrapper just names the
edge and aligns the output to the market return series.
"""

import numpy as np
import pytest

from markov.volmanaged import vol_managed_market


def test_returns_length_matches_input():
    mkt = np.random.default_rng(0).normal(0.0003, 0.01, 500)
    r = vol_managed_market(mkt, target_vol=0.15, window=20)
    assert len(r) == len(mkt)


def test_de_risks_in_high_vol_regime():
    # Calm then turbulent: leverage (exposure) should fall in turbulence.
    rng = np.random.default_rng(1)
    calm = rng.normal(0, 0.005, 200)
    wild = rng.normal(0, 0.04, 200)
    mkt = np.concatenate([calm, wild])
    r, lev = vol_managed_market(mkt, target_vol=0.15, window=20,
                                return_leverage=True)
    assert lev[210:].mean() < lev[150:200].mean()


def test_rejects_window_too_large():
    with pytest.raises(ValueError):
        vol_managed_market(np.ones(10), target_vol=0.15, window=20)
