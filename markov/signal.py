"""Signal generation (Step 5/8 of the hedge-fund method).

The trading signal is simply P(bull) - P(bear) for tomorrow, read off the
row of the transition matrix corresponding to today's state. The sign is
the direction (long if positive, short if negative) and the magnitude
scales the position size.
"""

from markov.states import State


def signal_from_row(row):
    """Signal from a single next-state distribution [P_bear, P_side, P_bull]."""
    return float(row[State.BULL] - row[State.BEAR])


def position_signal(P, today_state):
    """Signal for today's state, using its row of the transition matrix.

    Returns a value in [-1, 1]: positive -> long, negative -> short,
    magnitude -> conviction / position scale.
    """
    if today_state not in (State.BEAR, State.SIDEWAYS, State.BULL):
        raise ValueError(f"cannot generate a signal for state {today_state!r}")
    return signal_from_row(P[int(today_state)])
