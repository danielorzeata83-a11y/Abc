"""Tests for multi-step forecasting and the stationary distribution."""

import numpy as np
import pytest

from markov.states import State
from markov.transition import forecast, stationary_distribution


def _example_P():
    # Sticky bull/bear, leaky sideways. Rows sum to 1.
    return np.array([
        [0.70, 0.20, 0.10],   # from BEAR
        [0.25, 0.50, 0.25],   # from SIDEWAYS
        [0.10, 0.20, 0.70],   # from BULL
    ])


def test_forecast_one_day_is_identity_of_P():
    P = _example_P()
    np.testing.assert_allclose(forecast(P, 1), P)


def test_forecast_two_days_is_p_squared():
    P = _example_P()
    np.testing.assert_allclose(forecast(P, 2), P @ P)


def test_forecast_rows_stay_stochastic():
    P = _example_P()
    P5 = forecast(P, 5)
    np.testing.assert_allclose(P5.sum(axis=1), np.ones(3))


def test_forecast_rejects_zero_days():
    with pytest.raises(ValueError):
        forecast(_example_P(), 0)


def test_stationary_is_left_eigenvector():
    P = _example_P()
    pi = stationary_distribution(P)
    # pi @ P == pi, and sums to 1.
    np.testing.assert_allclose(pi @ P, pi, atol=1e-8)
    assert pi.sum() == pytest.approx(1.0)


def test_long_horizon_converges_to_stationary():
    P = _example_P()
    pi = stationary_distribution(P)
    P50 = forecast(P, 50)
    # Every row of P^50 should be (approximately) the stationary dist.
    for row in P50:
        np.testing.assert_allclose(row, pi, atol=1e-4)
