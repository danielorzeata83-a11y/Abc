"""Dashboard dip-watch: randuri sortate (cel mai adanc sus) cu stare colorabila,
si HTML self-contained (fara request-uri externe) care poarta disclaimerul."""

import numpy as np

from markov.dip_dashboard import build_html, dashboard_rows


def _top():
    return np.arange(1, 101, dtype=float)


def _deep():
    return np.concatenate([np.linspace(50, 100, 80), np.linspace(100, 55, 20)])


def test_rows_sorted_deep_first_with_state():
    rows = dashboard_rows([("TOP", _top()), ("FALL", _deep())],
                          lookback=60, dip=0.4)
    assert rows[0]["name"] == "FALL" and rows[0]["state"] == "deep"
    states = {r["name"]: r["state"] for r in rows}
    assert states["TOP"] == "near_top"


def test_nodata_row_is_marked_and_last():
    rows = dashboard_rows([("FALL", _deep()), ("SHORT", np.arange(5.0))],
                          lookback=60, dip=0.4)
    assert rows[-1]["name"] == "SHORT" and rows[-1]["state"] == "nodata"


def test_rows_carry_sparkline_and_threshold():
    rows = dashboard_rows([("FALL", _deep())], lookback=60, dip=0.4)
    r = rows[0]
    assert isinstance(r["spark"], list) and 2 <= len(r["spark"]) <= 120
    assert r["thr"] is not None and r["thr"] < r["price"] / (1 - 0.40) * 1.01


def test_build_html_self_contained_with_disclaimer():
    rows = dashboard_rows([("FALL", _deep())], lookback=60, dip=0.4)
    html = build_html(rows, asof="2026-06-07", dip=0.4)
    assert "<!DOCTYPE html>" in html
    assert "FALL" in html and "2026-06-07" in html
    assert '"spark"' in html and "<svg" in html.lower() or "svg" in html  # sparkline
    assert "consiliere de investi" in html.lower()
    assert "http://" not in html and "https://" not in html   # zero request extern
