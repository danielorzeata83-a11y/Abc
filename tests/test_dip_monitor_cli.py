"""Smoke pentru dip_monitor_cli: tabelul descriptiv + disclaimer."""

import numpy as np

import dip_monitor_cli as cli


def test_run_renders_table_and_disclaimer():
    top = np.arange(1, 101, dtype=float)                  # la maxim
    crashed = np.concatenate([np.linspace(50, 100, 80), np.linspace(100, 55, 20)])
    txt = cli.run([("TOP", top), ("FALL", crashed)],
                  lookback=60, dip=0.4, exit_ma=20)
    assert "MONITOR DIP-ADANC" in txt
    assert "aproape de maxim" in txt and "DIP ADANC" in txt
    assert "consiliere de investi" in txt.lower()
