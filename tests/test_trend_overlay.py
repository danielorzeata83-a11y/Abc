"""Tests for the hindsight-vs-real-time trend overlay primitives."""

import numpy as np
import pytest

from markov.trend_overlay import sma


def test_sma_trailing_average_with_nan_warmup():
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = sma(prices, window=3)
    assert np.isnan(out[0]) and np.isnan(out[1])
    assert out[2] == pytest.approx(2.0)   # mean(1,2,3)
    assert out[3] == pytest.approx(3.0)   # mean(2,3,4)
    assert out[4] == pytest.approx(4.0)   # mean(3,4,5)


def test_sma_rejects_nonpositive_window():
    with pytest.raises(ValueError):
        sma([1.0, 2.0], window=0)


from markov.trend_overlay import sma_crossovers, Crossover


def test_crossover_detects_single_golden_cross():
    # fast<slow then fast>slow -> exactly one golden cross, no death.
    # downtrend for the first half, uptrend for the second half.
    prices = list(np.linspace(100, 50, 30)) + list(np.linspace(50, 200, 30))
    xs = sma_crossovers(prices, fast=5, slow=20)
    kinds = [c.kind for c in xs]
    assert "golden" in kinds
    assert "death" not in kinds
    # golden cross happens during the recovery (second half)
    assert all(c.idx > 25 for c in xs if c.kind == "golden")


def test_crossover_none_on_monotonic_series():
    prices = list(np.linspace(10, 100, 60))   # always rising, fast stays above
    assert sma_crossovers(prices, fast=5, slow=20) == []


from markov.trend_overlay import hindsight_bottom


def test_hindsight_bottom_is_global_min_index():
    prices = [100.0, 80.0, 50.0, 70.0, 120.0]   # V-shape, min at idx 2
    assert hindsight_bottom(prices) == 2


def test_hindsight_bottom_rejects_empty():
    with pytest.raises(ValueError):
        hindsight_bottom([])


from markov.trend_overlay import lag_cost


def test_lag_cost_is_return_from_bottom_to_confirmation():
    prices = [100.0, 50.0, 60.0, 75.0]   # bottom idx 1 (=50), confirm idx 3 (=75)
    assert lag_cost(prices, bottom_idx=1, confirm_idx=3) == pytest.approx(0.5)


from markov.trend_overlay import count_whipsaws


def test_count_whipsaws_counts_quick_reversals():
    xs = [Crossover(10, "golden"), Crossover(15, "death"),   # 5 days  -> whipsaw
          Crossover(100, "golden"), Crossover(160, "death")] # 60 days -> ok
    assert count_whipsaws(xs, min_hold_days=30) == 1


def test_count_whipsaws_zero_when_all_held_long():
    xs = [Crossover(10, "golden"), Crossover(100, "death")]
    assert count_whipsaws(xs, min_hold_days=30) == 0
