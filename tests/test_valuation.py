"""Tests for the valuation thermometer (CAPE-based)."""

import numpy as np
import pytest
from markov.valuation import valuation_label, percentile_rank, implied_forward_return


def test_labels_by_threshold():
    assert valuation_label(9) == "CHEAP"
    assert valuation_label(17) == "NORMAL"
    assert valuation_label(32) == "EXPENSIVE"


def test_percentile_rank():
    hist = np.arange(1, 101.0)  # 1..100
    assert percentile_rank(50, hist) == pytest.approx(49.0, abs=1.0)
    assert percentile_rank(100, hist) == pytest.approx(99.0, abs=1.0)
    assert percentile_rank(1, hist) == pytest.approx(0.0, abs=1.0)


def test_implied_return_decreases_with_cape():
    rng = np.random.default_rng(0)
    hist_cape = rng.uniform(8, 35, 500)
    # true relationship: higher cape -> lower forward return
    hist_fwd = 0.12 - 0.003 * hist_cape + rng.normal(0, 0.01, 500)
    cheap = implied_forward_return(10, hist_cape, hist_fwd)
    pricey = implied_forward_return(30, hist_cape, hist_fwd)
    assert cheap > pricey
    # roughly tracks the true line
    assert abs(cheap - (0.12 - 0.003 * 10)) < 0.02


def test_implied_return_handles_degenerate():
    # all same cape -> just returns mean fwd
    hist_cape = np.full(50, 20.0)
    hist_fwd = np.full(50, 0.05)
    assert implied_forward_return(20, hist_cape, hist_fwd) == pytest.approx(0.05, abs=1e-6)
