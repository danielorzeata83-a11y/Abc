"""Tests for the zero-dependency SVG price chart."""

import numpy as np
import pandas as pd

from markov.trades import simulate_trades
from markov.svg_chart import scale_to_px, render_price_svg


def test_scale_to_px_maps_endpoints():
    # value at vmax -> top (small y), value at vmin -> bottom (large y)
    assert scale_to_px(10, 0, 10, top=0, bottom=100) == 0
    assert scale_to_px(0, 0, 10, top=0, bottom=100) == 100
    assert scale_to_px(5, 0, 10, top=0, bottom=100) == 50


def _scenario():
    dates = pd.bdate_range("2020-01-01", periods=6).to_numpy()
    close = np.array([100, 100, 102, 105, 111.0, 111])
    high = close + 1
    low = close - 1
    signal = np.array([0.0, 0.5, 0.5, 0.5, 0.5, 0.5])
    trades = simulate_trades(dates, high, low, close, signal,
                             sl_pct=0.05, tp_pct=0.10, max_hold=10)
    return dates, close, trades


def test_render_returns_svg_with_price_line():
    dates, close, trades = _scenario()
    svg = render_price_svg(dates, close, trades)
    assert svg.strip().startswith("<svg")
    assert svg.strip().endswith("</svg>")
    assert "<polyline" in svg


def test_render_marks_each_trade():
    dates, close, trades = _scenario()
    svg = render_price_svg(dates, close, trades)
    assert len(trades) >= 1
    # one entry marker (polygon triangle) per trade
    assert svg.count("<polygon") >= len(trades)
    # SL (red) and TP (green) reference lines present
    assert "#cf222e" in svg and "#1a7f37" in svg
    # native tooltips
    assert "<title>" in svg


def test_render_handles_no_trades():
    dates = pd.bdate_range("2020-01-01", periods=4).to_numpy()
    close = np.array([100, 101, 102, 103.0])
    svg = render_price_svg(dates, close, [])
    assert "<polyline" in svg and "<polygon" not in svg
