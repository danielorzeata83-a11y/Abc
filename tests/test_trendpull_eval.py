"""Evaluare trend-pullback: buy-and-hold pe felia OOS, serii OOS aliniate si
test de semnificatie agregat (pooled)."""

import numpy as np

from markov import trendpull_eval as ev
from markov.intraday.bars import Bars


def _bars(close, band=1.0):
    close = np.asarray(close, dtype=float)
    idx = np.arange(len(close)).astype("datetime64[D]")
    return Bars(idx, close, close + band, close - band, close,
                np.full(len(close), 1e6))


def _uptrend(n=240):
    t = np.arange(n)
    return 100 + 0.25 * t + 10 * np.sin(t / 6)


def test_bh_metrics_positive_on_uptrend():
    rng = np.random.default_rng(0)
    fwd = rng.normal(0.002, 0.01, 200)           # drift pozitiv -> B&H pozitiv
    m = ev.bh_metrics(fwd)
    assert m["bh_return"] > 0 and m["bh_sharpe"] > 0
    assert m["bh_max_drawdown"] <= 0.0


def test_oos_streams_aligned_and_mult_from_grid():
    chosen, pos, fwd = ev.select_oos_streams(_bars(_uptrend()),
                                             mults=(2.0, 3.0), split=0.5)
    assert chosen in (2.0, 3.0)
    assert len(pos) == len(fwd) and len(pos) > 0


def test_pooled_significance_one_test_over_streams():
    bars = _bars(_uptrend())
    s = ev.select_oos_streams(bars, mults=(2.0, 3.0), split=0.5)
    pooled = ev.pooled_significance([(s[1], s[2]), (s[1], s[2])], n_perm=100)
    assert 0.0 < pooled["p_value"] <= 1.0
    assert pooled["n_days"] == 2 * len(s[1])     # chiar concateneaza seriile
