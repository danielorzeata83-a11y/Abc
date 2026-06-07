"""Monitor dip-adanc: la maxim -> drawdown ~0, dupa cadere mare -> in zona dip,
pragul si distanta calculate corect. Descriptiv, fara semnal."""

import numpy as np

from markov.dipmonitor import dip_alert, dip_status


def _top():
    return np.arange(1, 101, dtype=float)


def _crashed():
    return np.concatenate([np.linspace(50, 100, 80), np.linspace(100, 55, 20)])


def test_alert_active_lists_deep_dip_name():
    a = dip_alert([("TOP", _top()), ("FALL", _crashed())], asof="2026-06-07")
    assert a["active"] is True
    assert "IN ZONA DE DIP ADANC" in a["text"] and "FALL" in a["text"]
    assert "consiliere de investi" in a["text"].lower()


def test_alert_quiet_when_nothing_qualifies():
    a = dip_alert([("TOP", _top())])
    assert a["active"] is False
    assert "Nimic in zona de dip adanc" in a["text"]


def test_at_new_high_is_near_top():
    close = np.arange(1, 101, dtype=float)        # mereu maxim nou
    s = dip_status(close, lookback=60, dip=0.4, exit_ma=20)
    assert s["drawdown"] >= -1e-9
    assert s["in_deep_dip"] is False
    assert s["label"] == "aproape de maxim"
    assert s["to_threshold"] < 0                   # mai trebuie sa cada mult


def test_deep_drop_enters_dip_zone():
    up = np.linspace(50, 100, 80)
    crash = np.linspace(100, 55, 20)              # -45% de la varf
    s = dip_status(np.concatenate([up, crash]), lookback=60, dip=0.4, exit_ma=20)
    assert s["in_deep_dip"] is True
    assert s["drawdown"] <= -0.4
    assert "DIP ADANC" in s["label"]
    assert s["to_threshold"] == 0.0                # deja sub prag


def test_shallow_correction_not_deep_dip():
    up = np.linspace(50, 100, 80)
    dip = np.linspace(100, 85, 10)                # doar -15%
    s = dip_status(np.concatenate([up, dip]), lookback=60, dip=0.4, exit_ma=20)
    assert s["in_deep_dip"] is False
    assert "corectie" in s["label"]
