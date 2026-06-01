"""Tests for Fibonacci swing detection and retracement levels."""

import numpy as np
import pytest
from markov.fibonacci import find_swings, fib_levels


def test_fib_levels_uptrend():
    lv = fib_levels(100.0, 200.0)  # up-leg, range 100
    assert lv[0.5] == pytest.approx(150.0)
    assert lv[0.382] == pytest.approx(161.8)
    assert lv[0.786] == pytest.approx(121.4)


def test_fib_levels_downtrend():
    lv = fib_levels(200.0, 100.0)  # down-leg; retrace UP from low
    assert lv[0.5] == pytest.approx(150.0)
    assert lv[0.382] == pytest.approx(138.2)


def test_find_swings_detects_peak_and_trough():
    prices = np.array([100.0, 130.0, 100.0])
    sw = find_swings(prices, threshold=0.1)
    types = [s[2] for s in sw]
    assert ("H" in types) and ("L" in types)
    # the high should be 130 at index 1
    highs = [s for s in sw if s[2] == "H"]
    assert highs[0][0] == 1 and highs[0][1] == pytest.approx(130.0)


def test_find_swings_alternate():
    prices = np.array([100, 130, 100, 140, 95, 150.0])
    sw = find_swings(prices, threshold=0.1)
    types = [s[2] for s in sw]
    # consecutive swings must alternate H/L
    assert all(types[i] != types[i + 1] for i in range(len(types) - 1))


def test_find_swings_monotonic_one_swing():
    prices = np.linspace(100, 120, 20)
    sw = find_swings(prices, threshold=0.05)
    assert len(sw) == 1 and sw[0][2] == "H"


def test_find_swings_empty_short():
    assert find_swings(np.array([100.0]), 0.05) == []
