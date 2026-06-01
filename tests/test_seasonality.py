"""Tests for the turn-of-month calendar edge.

The turn-of-month effect (Lakonishok & Smidt 1988): equity returns
cluster around the last few and first few trading days of each month.
Hold the market only on those days, stay flat otherwise. The calendar is
known in advance, so there is no look-ahead. Low turnover -> cost-robust,
and its mechanism is independent of cross-sectional reversal.
"""

import numpy as np
import pandas as pd
import pytest

from markov.seasonality import turn_of_month_mask, turn_of_month_returns


def _dates(n):
    return pd.bdate_range("2015-01-01", periods=n).to_numpy()


def test_mask_flags_month_boundaries_only():
    dates = _dates(60)
    mask = turn_of_month_mask(dates, n_end=3, n_start=3)
    assert mask.dtype == bool
    assert len(mask) == len(dates)
    # Should be in-market a minority of the time.
    assert 0.0 < mask.mean() < 0.6


def test_returns_zero_off_calendar_days():
    dates = _dates(60)
    mkt = np.full(len(dates), 0.01)
    r = turn_of_month_returns(mkt, dates, n_end=3, n_start=3)
    mask = turn_of_month_mask(dates, n_end=3, n_start=3)
    # Off-calendar days contribute exactly zero.
    assert np.all(r[~mask] == 0.0)
    assert np.all(r[mask] == 0.01)


def test_length_matches_input():
    dates = _dates(100)
    mkt = np.random.default_rng(0).normal(0, 0.01, len(dates))
    r = turn_of_month_returns(mkt, dates)
    assert len(r) == len(mkt)


def test_rejects_length_mismatch():
    dates = _dates(50)
    with pytest.raises(ValueError):
        turn_of_month_returns(np.zeros(40), dates)
