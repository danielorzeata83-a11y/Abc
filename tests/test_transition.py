"""Tests for the Markov transition matrix (Step 3-4).

Given a sequence of states, count transitions state[t] -> state[t+1]
and normalise each row to a probability distribution. UNKNOWN states
are excluded. Rows for states never observed default to uniform (or are
flagged) — see tests below.
"""

import numpy as np
import pytest

from markov.states import State
from markov.transition import transition_matrix


def test_pure_bull_sequence_is_sticky():
    seq = [State.BULL] * 10
    P = transition_matrix(seq)
    # Always bull->bull => P[BULL,BULL] == 1.0
    assert P[State.BULL, State.BULL] == pytest.approx(1.0)


def test_rows_sum_to_one():
    seq = [State.BULL, State.BEAR, State.SIDEWAYS, State.BULL,
           State.SIDEWAYS, State.BEAR, State.BULL, State.BULL]
    P = transition_matrix(seq)
    assert P.shape == (3, 3)
    np.testing.assert_allclose(P.sum(axis=1), np.ones(3))


def test_counts_are_correct():
    # bull->bear once, bear->sideways once, sideways->bull once, bull->bull once
    seq = [State.BULL, State.BEAR, State.SIDEWAYS, State.BULL, State.BULL]
    P = transition_matrix(seq)
    assert P[State.BULL, State.BEAR] == pytest.approx(0.5)   # bull seen 2x before next
    assert P[State.BULL, State.BULL] == pytest.approx(0.5)
    assert P[State.BEAR, State.SIDEWAYS] == pytest.approx(1.0)
    assert P[State.SIDEWAYS, State.BULL] == pytest.approx(1.0)


def test_unknown_states_are_ignored():
    seq = [State.UNKNOWN, State.UNKNOWN, State.BULL, State.BULL]
    P = transition_matrix(seq)
    # Only the bull->bull transition counts.
    assert P[State.BULL, State.BULL] == pytest.approx(1.0)


def test_unobserved_state_row_defaults_uniform():
    # No BEAR transitions observed -> that row should be uniform 1/3.
    seq = [State.BULL, State.SIDEWAYS, State.BULL, State.SIDEWAYS]
    P = transition_matrix(seq)
    np.testing.assert_allclose(P[State.BEAR], np.full(3, 1 / 3))


def test_rejects_empty_sequence():
    with pytest.raises(ValueError):
        transition_matrix([])
