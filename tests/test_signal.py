"""Tests for signal generation (Step 5/8).

Signal = P(bull tomorrow) - P(bear tomorrow), given today's state.
Sign gives direction (long/short); magnitude (in [-1, 1]) scales the
position size.
"""

import numpy as np
import pytest

from markov.states import State
from markov.signal import signal_from_row, position_signal


def test_signal_is_bull_minus_bear():
    # row = [bear, sideways, bull] = [0.20, 0.15, 0.65]
    row = np.array([0.20, 0.15, 0.65])
    assert signal_from_row(row) == pytest.approx(0.45)


def test_negative_signal_means_short():
    row = np.array([0.60, 0.15, 0.25])  # bear-heavy
    assert signal_from_row(row) < 0


def test_signal_bounded_in_unit_interval():
    for _ in range(100):
        r = np.random.dirichlet([1, 1, 1])
        s = signal_from_row(r)
        assert -1.0 <= s <= 1.0


def test_position_signal_uses_todays_state_row():
    P = np.array([
        [0.70, 0.20, 0.10],   # BEAR row -> signal 0.10 - 0.70 = -0.60
        [0.25, 0.50, 0.25],   # SIDEWAYS -> 0.0
        [0.10, 0.20, 0.70],   # BULL row -> 0.70 - 0.10 = +0.60
    ])
    assert position_signal(P, State.BEAR) == pytest.approx(-0.60)
    assert position_signal(P, State.SIDEWAYS) == pytest.approx(0.0)
    assert position_signal(P, State.BULL) == pytest.approx(0.60)


def test_position_signal_rejects_unknown_state():
    P = np.full((3, 3), 1 / 3)
    with pytest.raises(ValueError):
        position_signal(P, State.UNKNOWN)
