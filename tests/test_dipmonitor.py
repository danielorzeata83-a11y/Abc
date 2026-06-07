"""Monitor dip-adanc: la maxim -> drawdown ~0, dupa cadere mare -> in zona dip,
pragul si distanta calculate corect. Descriptiv, fara semnal."""

import numpy as np

from markov.dipmonitor import dip_status


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
