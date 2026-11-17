"""Retea lead-lag cross-asset: aliniere randamente + clasament lider/urmaritor."""

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation.crossasset import (aligned_returns, lead_lag_matrix,
                                          render_lead_lag)


def _seed_daily(dirpath, symbol, rets):
    """Scrie bare daily al caror randament zilnic e `rets` (close cumulat)."""
    n = len(rets) + 1
    idx = pd.bdate_range("2010-01-04", periods=n)
    close = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + rets)))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_lead_lag_ranks_driver_above_follower(tmp_path):
    """A conduce B conduce C: scorul net A > C."""
    rng = np.random.default_rng(0)
    n = 4000
    a = rng.normal(0, 0.01, size=n)
    b = np.empty(n); b[0] = 0.0; b[1:] = a[:-1] + 0.002 * rng.normal(size=n - 1)
    c = np.empty(n); c[0] = 0.0; c[1:] = b[:-1] + 0.002 * rng.normal(size=n - 1)
    d = str(tmp_path)
    _seed_daily(d, "A", a); _seed_daily(d, "B", b); _seed_daily(d, "C", c)

    rets = aligned_returns(["A", "B", "C"], d)
    assert list(rets.columns) == ["A", "B", "C"]
    syms, M, net = lead_lag_matrix(rets, bins=4, lag=1)
    score = dict(zip(syms, net))
    assert score["A"] > score["C"]                 # sursa peste destinatie
    assert M[syms.index("A"), syms.index("B")] > M[syms.index("B"), syms.index("A")]


def test_aligned_returns_intersects_dates(tmp_path):
    d = str(tmp_path)
    _seed_daily(d, "A", np.full(100, 0.001))
    _seed_daily(d, "B", np.full(60, 0.001))        # mai scurt
    rets = aligned_returns(["A", "B"], d)
    assert len(rets) <= 60                          # doar datele comune
    assert not rets.isna().any().any()


def test_render_lead_lag_has_disclaimer_and_ranking(tmp_path):
    d = str(tmp_path)
    rng = np.random.default_rng(1)
    for s in ("A", "B"):
        _seed_daily(d, s, rng.normal(0, 0.01, size=500))
    syms, M, net = lead_lag_matrix(aligned_returns(["A", "B"], d))
    txt = render_lead_lag(syms, M, net)
    assert "consiliere de investi" in txt.lower()
    assert "lider" in txt and "lead-lag" in txt.lower()
