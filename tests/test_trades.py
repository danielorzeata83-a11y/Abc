"""Tests for the discrete trade simulator (signal -> entry/SL/TP/exit).

NOTE: this is a discrete-trade OVERLAY on the continuous signals; it is a
visualisation/interpretation layer, NOT a validated strategy.
"""

import numpy as np
import pandas as pd
import pytest

from markov.trades import simulate_trades, Trade


def _dates(n):
    return pd.bdate_range("2020-01-01", periods=n).to_numpy()


def test_long_take_profit_hit():
    # Flat then BUY; price rises to TP.
    close = np.array([100, 100, 102, 105, 111.0])
    high = np.array([100, 100, 103, 106, 112.0])
    low = np.array([100, 100, 101, 104, 110.0])
    signal = np.array([0.0, 0.5, 0.5, 0.5, 0.5])  # BUY from idx 1
    trades = simulate_trades(_dates(5), high, low, close, signal,
                             sl_pct=0.05, tp_pct=0.10, max_hold=10)
    assert len(trades) == 1
    t = trades[0]
    assert t.side == "long"
    assert t.entry_px == 100  # entered at close of idx 1
    assert t.reason == "TP"
    assert t.ret > 0 and t.r_multiple == pytest.approx(2.0, abs=0.01)


def test_long_stop_loss_hit():
    close = np.array([100, 100, 98, 95.0])
    high = np.array([100, 100, 99, 96.0])
    low = np.array([100, 100, 97, 94.0])   # breaches 95 stop
    signal = np.array([0.0, 0.5, 0.5, 0.5])
    trades = simulate_trades(_dates(4), high, low, close, signal,
                             sl_pct=0.05, tp_pct=0.10, max_hold=10)
    assert trades[0].reason == "SL"
    assert trades[0].ret < 0


def test_exit_on_signal_flip():
    close = np.array([100, 100, 101, 101.0, 101])
    high = close + 1
    low = close - 1
    signal = np.array([0.0, 0.5, 0.5, -0.5, -0.5])  # flips to SELL at idx 3
    trades = simulate_trades(_dates(5), high, low, close, signal,
                             sl_pct=0.10, tp_pct=0.20, max_hold=10)
    # First long exits on flip; then a short opens.
    assert trades[0].reason == "flip"
    assert any(t.side == "short" for t in trades)


def test_timeout_exit():
    close = np.full(10, 100.0)
    signal = np.concatenate([[0.0], np.full(9, 0.5)])
    trades = simulate_trades(_dates(10), close + 1, close - 1, close, signal,
                             sl_pct=0.5, tp_pct=0.5, max_hold=3)
    assert trades[0].reason == "timeout"


def test_no_trades_when_signal_below_threshold():
    close = np.full(6, 100.0)
    signal = np.full(6, 0.05)  # below default threshold
    trades = simulate_trades(_dates(6), close, close, close, signal)
    assert trades == []
