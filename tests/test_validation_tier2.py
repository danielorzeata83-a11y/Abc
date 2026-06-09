"""TIER 2: familia de factori time-series ca serii cauzale, aceeasi semnatura
ca TIER 1. Verifica forma, semnul pe serii sintetice si lipsa look-ahead-ului."""

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.validation import tier2


def _bars(close, start="2015-01-02"):
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range(start, periods=len(close))
    return Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                np.full(len(close), 1e6))


def test_all_indicators_return_bar_aligned_series():
    b = _bars(100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 300)))
    for name, fn in tier2.INDICATORS.items():
        out = np.asarray(fn(b))
        assert out.shape == (len(b),), name


def test_ts_momentum_positive_in_uptrend_negative_in_downtrend():
    up = tier2.ts_momentum(_bars(100 * 1.01 ** np.arange(120)))
    down = tier2.ts_momentum(_bars(100 * 0.99 ** np.arange(120)))
    assert up[-1] > 0 and down[-1] < 0


def test_ts_reversal_positive_after_drop():
    # urcare lina apoi o cadere brusca la coada -> semnal de revenire pozitiv
    c = np.concatenate([100 + np.arange(50) * 0.1, [105, 104, 103, 100, 96]])
    assert tier2.ts_reversal(_bars(c))[-1] > 0


def test_low_vol_ranks_calm_above_turbulent():
    rng = np.random.default_rng(1)
    calm = 100 + np.cumsum(rng.normal(0, 0.1, 200))
    wild = 100 + np.cumsum(rng.normal(0, 2.0, 200))
    assert tier2.low_vol(_bars(calm))[-1] > tier2.low_vol(_bars(wild))[-1]


def test_vol_managed_higher_when_calmer():
    rng = np.random.default_rng(2)
    calm = 100 + np.cumsum(rng.normal(0, 0.1, 120))
    wild = 100 + np.cumsum(rng.normal(0, 2.0, 120))
    assert tier2.vol_managed(_bars(calm))[-1] > tier2.vol_managed(_bars(wild))[-1]


def test_turn_of_month_is_binary_and_marks_some_days():
    tom = tier2.turn_of_month(_bars(100 + np.zeros(120)))
    assert set(np.unique(tom)) <= {0.0, 1.0}
    assert 0 < tom.sum() < len(tom)


def test_no_lookahead_value_at_t_unchanged_by_future():
    rng = np.random.default_rng(3)
    c = 100 + np.cumsum(rng.normal(0, 1, 200))
    b_full = _bars(c)
    t = 150
    b_trunc = _bars(c[:t + 1])
    for name, fn in tier2.INDICATORS.items():
        full = np.asarray(fn(b_full))[t]
        trunc = np.asarray(fn(b_trunc))[t]
        if np.isfinite(full) or np.isfinite(trunc):
            assert np.allclose(full, trunc, equal_nan=True), name
