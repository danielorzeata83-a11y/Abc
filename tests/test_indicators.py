"""Tests for classic technical indicators (mechanical, testable)."""

import numpy as np
import pytest
from markov.indicators import rsi, macd, stochastic_k


def test_rsi_all_gains_near_100():
    prices = np.arange(1, 50, dtype=float)  # monotonic up
    r = rsi(prices, period=14)
    assert r[-1] > 99


def test_rsi_all_losses_near_0():
    prices = np.arange(50, 1, -1, dtype=float)
    r = rsi(prices, period=14)
    assert r[-1] < 1


def test_rsi_range_and_length():
    rng = np.random.default_rng(0)
    prices = 100 + np.cumsum(rng.normal(0, 1, 200))
    r = rsi(prices, 14)
    assert len(r) == len(prices)
    valid = r[~np.isnan(r)]
    assert valid.min() >= 0 and valid.max() <= 100


def test_macd_line_and_signal_lengths():
    prices = 100 + np.cumsum(np.random.default_rng(1).normal(0, 1, 200))
    line, sig, hist = macd(prices)
    assert len(line) == len(sig) == len(hist) == len(prices)


def test_macd_positive_in_uptrend():
    prices = np.arange(1, 100, dtype=float)
    line, sig, hist = macd(prices)
    assert line[-1] > 0


def test_stochastic_range():
    prices = 100 + np.cumsum(np.random.default_rng(2).normal(0, 1, 100))
    k = stochastic_k(prices, period=14)
    valid = k[~np.isnan(k)]
    assert valid.min() >= 0 and valid.max() <= 100
