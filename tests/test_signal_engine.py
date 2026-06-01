"""Tests for the Signal contract and position->label/confidence mapping."""

import pytest

from markov.signal_engine import Signal, classify_position


def test_classify_buy_sell_hold_by_threshold():
    assert classify_position(0.30, threshold=0.15)[0] == "BUY"
    assert classify_position(-0.30, threshold=0.15)[0] == "SELL"
    assert classify_position(0.05, threshold=0.15)[0] == "HOLD"


def test_confidence_is_scaled_magnitude_in_unit_range():
    _, conf = classify_position(0.5, threshold=0.15)
    assert 0.0 <= conf <= 1.0
    # Larger magnitude -> higher confidence.
    assert classify_position(0.8, threshold=0.15)[1] > \
        classify_position(0.2, threshold=0.15)[1]


def test_position_clamped_into_unit_range():
    s = Signal.from_position(1.8, breakdown={"x": 1.8}, mode="time-series")
    assert s.position == 1.0
    s2 = Signal.from_position(-2.0, breakdown={}, mode="cross-sectional")
    assert s2.position == -1.0


def test_signal_carries_label_confidence_mode_breakdown():
    s = Signal.from_position(0.4, breakdown={"Rev3": 0.4, "ResMom": 0.4},
                             mode="cross-sectional", threshold=0.15)
    assert s.label == "BUY"
    assert 0.0 <= s.confidence <= 1.0
    assert s.mode == "cross-sectional"
    assert set(s.breakdown) == {"Rev3", "ResMom"}


def test_low_confidence_flag_for_time_series_mode():
    s = Signal.from_position(0.4, breakdown={"TSmom": 0.4}, mode="time-series")
    # Time-series single-asset signals are flagged as low confidence.
    assert s.low_confidence is True
    s2 = Signal.from_position(0.4, breakdown={}, mode="cross-sectional")
    assert s2.low_confidence is False


def test_render_contains_label_and_disclaimer():
    s = Signal.from_position(0.4, breakdown={"Rev3": 0.4},
                             mode="cross-sectional", ticker="NVDA")
    text = s.render()
    assert "NVDA" in text and "BUY" in text
    assert "not investment advice" in text.lower()
