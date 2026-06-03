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
