"""Raport motor -> Telegram: semnal vol, etichete, mesaj din cache."""

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import alert


def _seed_daily(dirpath, symbol, rets):
    n = len(rets) + 1
    idx = pd.bdate_range("2010-01-04", periods=n)
    close = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + rets)))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_current_vol_signal_high_after_spike():
    """Vol mica apoi un puseu la coada -> z-score curent ridicat (>1)."""
    rng = np.random.default_rng(0)
    calm = rng.normal(0, 0.005, size=400)
    storm = rng.normal(0, 0.05, size=40)
    rets = np.concatenate([calm, storm])
    idx = pd.bdate_range("2010-01-04", periods=len(rets) + 1)
    close = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + rets)))
    bars = Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                np.full(len(close), 1e6))
    assert alert.current_vol_signal(bars) > 1.0


def test_vol_label_tiers():
    assert "RIDICATA" in alert._vol_label(1.5)
    assert alert._vol_label(0.0) == "normala"
    assert alert._vol_label(-1.5) == "SCAZUTA"
    assert alert._vol_label(float("nan")) == "fara date"


def test_build_engine_alert_has_sections_and_disclaimer():
    msg = alert.build_engine_alert(
        "2026-06-03",
        [("NVDA", 1.8, "RIDICATA -> redu expunerea"), ("AAPL", -0.3, "normala")],
        [("NVDA", 0.012), ("TSLA", -0.008)])
    assert "VOLATILITATE" in msg and "LEAD-LAG" in msg
    assert "NVDA" in msg and "lider" in msg and "urmaritor" in msg
    assert "consiliere de investi" in msg.lower()


def test_staleness_note_flags_old_data():
    assert alert._staleness_note("2026-06-04", "2026-06-03") == ""   # proaspat
    assert "vechi de" in alert._staleness_note("2026-06-04", "2026-05-01")
    assert alert._staleness_note("2026-06-04", None) == ""


def test_build_engine_alert_shows_data_date_and_staleness():
    fresh = alert.build_engine_alert("2026-06-04", [("AAA", 0.1, "normala")],
                                     [("AAA", 0.0)], data_asof="2026-06-03")
    assert "date pana la: 2026-06-03" in fresh and "ATENTIE" not in fresh
    stale = alert.build_engine_alert("2026-06-04", [("AAA", 0.1, "normala")],
                                     [("AAA", 0.0)], data_asof="2026-01-01")
    assert "ATENTIE" in stale and "backfill" in stale


def test_build_from_cache_end_to_end(tmp_path):
    d = str(tmp_path)
    rng = np.random.default_rng(1)
    a = rng.normal(0, 0.01, size=600)
    b = np.empty(600); b[0] = 0.0; b[1:] = a[:-1] + 0.002 * rng.normal(size=599)
    _seed_daily(d, "AAA", a); _seed_daily(d, "BBB", b)
    msg = alert.build_from_cache(["AAA", "BBB"], d, "2026-06-03")
    assert "AAA" in msg and "BBB" in msg
    assert "VOLATILITATE" in msg and "LEAD-LAG" in msg
