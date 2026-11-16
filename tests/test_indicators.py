import math

import pytest

from sensa import indicators as ind


def bars(closes, vols=None, t0=1_700_000_000, step=900):
    vols = vols or [100] * len(closes)
    return [{"time": t0 + i * step, "open": c, "high": c + 1, "low": c - 1, "close": c, "volume": v}
            for i, (c, v) in enumerate(zip(closes, vols))]


def vals(series):
    return [p["value"] for p in series]


def test_sma_waits_for_the_window():
    s = ind.sma([1, 2, 3, 4, 5], 3)
    assert s == [None, None, 2, 3, 4]


def test_ema_seeds_with_sma_and_follows_the_alpha():
    s = ind.ema([1, 2, 3, 4, 5], 3)
    assert s[:2] == [None, None] and s[2] == pytest.approx(2)
    assert s[3] == pytest.approx(3) and s[4] == pytest.approx(4)       # alpha 0.5 on a straight line


def test_vwma_weights_by_volume():
    s = ind.vwma([10, 20], [1, 3], 2)
    assert s[1] == pytest.approx((10 * 1 + 20 * 3) / 4)


def test_vwema_equals_ema_for_equal_volume():
    c = [1, 3, 2, 5, 4, 6]
    a, b = ind.vwema(c, [7] * 6, 3), ind.ema(c, 3)
    for x, y in zip(a, b):
        assert (x is None and y is None) or x == pytest.approx(y)


def test_vwap_resets_each_day_for_intraday():
    day = 86400
    b = [{"time": 1_700_000_000 + i * 900, "open": p, "high": p, "low": p, "close": p, "volume": 10} for i, p in enumerate([10, 20])]
    b += [{"time": 1_700_000_000 + day + i * 900, "open": p, "high": p, "low": p, "close": p, "volume": 10} for i, p in enumerate([30, 50])]
    r = ind.vwap(b, mode="session")
    v = [p["value"] for p in r["vwap"]]
    assert v == pytest.approx([10, 15, 30, 40])


def test_vwap_anchored_ignores_bars_before_the_anchor():
    b = bars([10, 20, 30, 50])
    r = ind.vwap(b, anchor=b[2]["time"])
    assert [p["time"] for p in r["vwap"]] == [b[2]["time"], b[3]["time"]]
    assert vals(r["vwap"]) == pytest.approx([30, 40])


def test_vwap_bands_are_symmetric_and_widen_with_dispersion():
    b = bars([10, 20, 10, 20])
    r = ind.vwap(b, anchor=b[0]["time"])
    up, dn, mid = vals(r["upper1"]), vals(r["lower1"]), vals(r["vwap"])
    assert up[0] == pytest.approx(mid[0]) and up[3] > mid[3]
    assert [u - m for u, m in zip(up, mid)] == pytest.approx([m - d for m, d in zip(mid, dn)])
    assert vals(r["upper2"])[3] - mid[3] == pytest.approx(2 * (up[3] - mid[3]))


def test_vwap_momentum_is_the_percent_distance_of_close_to_vwap():
    b = bars([10, 20])
    r = ind.vwap(b, anchor=b[0]["time"])
    m = vals(r["momentum"])
    assert m[0] == pytest.approx((10 - 10) / 10 * 100) and m[1] == pytest.approx((20 - 15) / 15 * 100)


def test_daily_default_anchors_at_the_start_of_the_year_of_the_last_bar():
    b = [{"time": d, "open": 1, "high": 1, "low": 1, "close": c, "volume": 1}
         for d, c in (("2025-12-30", 100), ("2026-01-02", 10), ("2026-01-05", 20))]
    r = ind.vwap(b)
    assert [p["time"] for p in r["vwap"]] == ["2026-01-02", "2026-01-05"]


def test_ema_cloud_gives_two_lines_and_the_direction():
    r = ind.ema_cloud(list(range(1, 60)), 8, 21)
    assert len(r["fast"]) == len(r["slow"]) and r["bullish"][-1] is True


def test_bollinger_bands_bracket_the_mean():
    c = [1, 2, 3, 4, 5, 6]
    mid, up, lo = ind.bollinger(c, 3, 2)
    assert mid[2] == pytest.approx(2)
    sd = math.sqrt(sum((x - 2) ** 2 for x in (1, 2, 3)) / 3)
    assert up[2] == pytest.approx(2 + 2 * sd) and lo[2] == pytest.approx(2 - 2 * sd)


def test_rsi_extremes():
    assert ind.rsi(list(range(1, 40)), 14)[-1] == pytest.approx(100)
    assert ind.rsi(list(range(40, 1, -1)), 14)[-1] == pytest.approx(0)
    assert ind.rsi([1, 2, 3], 14) == [None, None, None]


def test_macd_histogram_is_line_minus_signal():
    line, sig, hist = ind.macd(list(range(1, 80)))
    i = -1
    assert hist[i] == pytest.approx(line[i] - sig[i])


def test_compute_returns_time_value_series_for_everything():
    b = bars([100 + (i % 7) + i * 0.1 for i in range(260)], [100 + i for i in range(260)])
    r = ind.compute(b)
    for k in ("sma20", "sma50", "sma200", "ema9", "ema21", "vwma20", "vwema20", "bb_mid", "bb_upper", "bb_lower",
              "rsi14", "macd", "macd_signal", "macd_hist", "vwap", "vwap_upper1", "vwap_lower2", "vwap_momentum",
              "cloud_fast", "cloud_slow"):
        assert r[k] and set(r[k][0]) >= {"time", "value"}, k
    assert r["cloud_dir"][-1]["value"] in (1, -1)
    assert len(r["sma200"]) == 260 - 199


def test_compute_handles_too_few_bars():
    r = ind.compute(bars([1, 2, 3]))
    assert r["sma200"] == [] and r["rsi14"] == []
