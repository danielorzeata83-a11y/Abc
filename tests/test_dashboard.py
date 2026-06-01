"""Tests for dashboard rendering logic (pure functions)."""

from markov.signal_engine import Signal
from markov.dashboard import rank_signals, render_table, render_html


def _sig(ticker, pos):
    return Signal.from_position(pos, breakdown={"reversal": pos},
                                mode="cross-sectional", ticker=ticker)


def _signals():
    return [_sig("AAA", 0.6), _sig("BBB", -0.7), _sig("CCC", 0.05),
            _sig("DDD", 0.3)]


def test_rank_signals_sorted_by_position_desc():
    ranked = rank_signals(_signals())
    positions = [s.position for s in ranked]
    assert positions == sorted(positions, reverse=True)
    assert ranked[0].ticker == "AAA"
    assert ranked[-1].ticker == "BBB"


def test_render_table_contains_all_tickers_and_labels():
    txt = render_table(_signals())
    for t in ["AAA", "BBB", "CCC", "DDD"]:
        assert t in txt
    assert "BUY" in txt and "SELL" in txt and "HOLD" in txt
    assert "not investment advice" in txt.lower()


def test_render_table_top_n_limits_rows():
    txt = render_table(_signals(), top_n=1)
    # Only the strongest buy and strongest sell shown.
    assert "AAA" in txt and "BBB" in txt
    assert "CCC" not in txt


def test_render_html_is_valid_ish_html():
    html = render_html(_signals(), title="Tech")
    assert html.strip().startswith("<!DOCTYPE html>")
    assert "<table" in html and "AAA" in html and "Tech" in html
    assert "not investment advice" in html.lower()
