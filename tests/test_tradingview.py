"""Trading view HTML: panel din bare, HTML self-contained (fara cereri externe)."""

import json
import re

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov import tradingview
import tradingview_cli


def _bars(n=120, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    idx = pd.bdate_range("2020-01-02", periods=n)
    return Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                rng.uniform(1e6, 5e6, n))


def test_panel_for_symbol_shape_and_volz():
    p = tradingview.panel_for_symbol("NVDA", _bars())
    assert p["symbol"] == "NVDA"
    for k in ("dates", "o", "h", "l", "c", "v", "volz", "ma"):
        assert len(p[k]) == 120
    assert any(z is not None for z in p["volz"])          # seria de vol exista
    assert p["dates"][0] == "2020-01-02"


def test_panel_has_ma50_and_crossover_signals():
    p = tradingview.panel_for_symbol("NVDA", _bars(n=200, seed=1))
    assert p["ma"][:49] == [None] * 49                    # MA50 nan pana la 50 bare
    assert p["ma"][60] is not None
    assert all(s["type"] in ("BUY", "SELL") for s in p["signals"])
    assert all(0 <= s["i"] < 200 for s in p["signals"])


def test_lead_lag_ranking_orders_by_net(tmp_path):
    d = str(tmp_path)
    write_bars(d, "AAA", _bars(seed=1))
    write_bars(d, "BBB", _bars(seed=2))
    ll = tradingview.lead_lag_ranking(["AAA", "BBB"], d)
    assert {r["symbol"] for r in ll} == {"AAA", "BBB"}
    assert ll[0]["net"] >= ll[-1]["net"]                  # sortat descrescator


def test_lead_lag_ranking_empty_on_missing(tmp_path):
    assert tradingview.lead_lag_ranking(["NOPE"], str(tmp_path)) == []


def test_build_html_is_self_contained():
    p = tradingview.panel_for_symbol("NVDA", _bars())
    html = tradingview.build_html([p], "2026-06-04")
    assert html.startswith("<!DOCTYPE html>")
    assert "NVDA" in html and "z realized_var" in html
    assert "consiliere de investi" in html.lower()
    # fara resurse externe: nicio referinta http(s) catre CDN/scripturi
    assert not re.search(r'(src|href)\s*=\s*["\']https?://', html)


def test_build_html_embeds_valid_json():
    p = tradingview.panel_for_symbol("AAA", _bars(seed=3))
    html = tradingview.build_html([p], "2026-06-04")
    m = re.search(r"const DATA = (\{.*?\});", html, re.S)
    assert m
    data = json.loads(m.group(1))
    assert data["asof"] == "2026-06-04"
    assert data["panels"][0]["symbol"] == "AAA"
    assert "leadlag" in data


def test_build_html_embeds_leadlag():
    p = tradingview.panel_for_symbol("AAA", _bars())
    ll = [{"symbol": "AAA", "net": 0.01}, {"symbol": "BBB", "net": -0.01}]
    html = tradingview.build_html([p], "2026-06-04", leadlag=ll)
    m = re.search(r"const DATA = (\{.*?\});", html, re.S)
    data = json.loads(m.group(1))
    assert data["leadlag"][0]["symbol"] == "AAA"


def test_collect_panels_reads_cache_and_skips_missing(tmp_path):
    d = str(tmp_path)
    write_bars(d, "AAA", _bars(seed=1))
    write_bars(d, "BBB", _bars(seed=2))
    panels = tradingview.collect_panels(["AAA", "BBB", "ZZZ"], d)
    assert [p["symbol"] for p in panels] == ["AAA", "BBB"]   # ZZZ lipsa -> sarit


def test_collect_panels_caps_max_bars(tmp_path):
    d = str(tmp_path)
    write_bars(d, "AAA", _bars(n=900, seed=4))
    panels = tradingview.collect_panels(["AAA"], d, max_bars=300)
    assert len(panels[0]["c"]) == 300


def test_cli_writes_html(tmp_path):
    d = str(tmp_path)
    write_bars(d, "AAA", _bars(seed=5))
    out = tmp_path / "tv.html"
    tradingview_cli.main(["--symbols", "AAA", "--data-dir", d, "--out", str(out)])
    html = out.read_text(encoding="utf-8")
    assert "<canvas" in html and "AAA" in html
    assert "consiliere de investi" in html.lower()
