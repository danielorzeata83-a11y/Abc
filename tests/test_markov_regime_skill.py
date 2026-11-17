"""Smoke pentru scriptul skill-ului markov-regime: raportul contine sectiunile
cheie (stare, tranzitie, backtest) si disclaimerul; ruleaza pe Bars sintetice."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars

_SCRIPT = (Path(__file__).resolve().parents[1]
           / ".claude/skills/markov-regime/scripts/regime.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("regime_skill", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bars(n=400, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0.0004, 0.012, n))
    idx = pd.bdate_range("2018-01-02", periods=n)
    return Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                rng.uniform(1e6, 5e6, n))


def test_report_has_sections_and_disclaimer():
    mod = _load_module()
    b = _bars()
    txt = mod.regime_report("AAA", b.timestamps, np.asarray(b.close, dtype=float), b,
                            hmm=False)              # fara HMM: rapid, fara hmmlearn
    assert "Regim de piata: AAA" in txt
    assert "STARE MARKOV" in txt and "BACKTEST WALK-FORWARD" in txt
    assert "consiliere de investi" in txt.lower()


def test_backtest_can_be_skipped():
    mod = _load_module()
    b = _bars(seed=2)
    txt = mod.regime_report("BBB", b.timestamps, np.asarray(b.close, dtype=float), b,
                            backtest=False, hmm=False)
    assert "BACKTEST WALK-FORWARD" not in txt
