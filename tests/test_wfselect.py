"""Selectorul walk-forward generic: alege param din grila, raporteaza OOS,
serii OOS aliniate."""

import numpy as np

from markov import wfselect
from markov.intraday.bars import Bars


def _bars(close):
    close = np.asarray(close, dtype=float)
    idx = np.arange(len(close)).astype("datetime64[D]")
    return Bars(idx, close, close + 1, close - 1, close, np.full(len(close), 1e6))


def _const_long(bars, value):
    # ignora value: mereu long -> selectorul trebuie sa ruleze fara sa crape
    return np.ones(len(bars))


def test_select_param_returns_oos_and_choice_from_grid():
    bars = _bars(100 * np.cumprod(1 + np.random.default_rng(0).normal(0.001, 0.01, 200)))
    res = wfselect.select_param(_const_long, bars, grid=[0.1, 0.2], n_perm=50)
    assert res["chosen"] in [0.1, 0.2]
    assert set(res["oos"]) >= {"net_return", "sharpe", "p_value"}


def test_oos_streams_aligned():
    bars = _bars(np.linspace(100, 150, 180))
    chosen, pos, fwd = wfselect.oos_streams(_const_long, bars, grid=[0.1, 0.3])
    assert chosen in [0.1, 0.3]
    assert len(pos) == len(fwd) and len(pos) > 0
