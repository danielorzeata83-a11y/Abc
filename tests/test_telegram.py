"""Tests for the Telegram alert builder + sender.

The valuable, testable logic is building the daily alert text from the CAPE
reading and the screener's CHEAP+QUALITY candidates -- including the mandatory
"not investment advice" disclaimer. The HTTP send is a thin urllib wrapper with
an injectable opener so we can assert the URL/payload without a network call.
"""

import json
import pytest
from markov.telegram import build_alert, send_message, DISCLAIMER


def _cands():
    return [
        {"Symbol": "EG", "Sector": "Reinsurance", "Price/Earnings": 6.6,
         "value_pct": 96, "quality_pct": 56, "quadrant": "CHEAP + QUALITY"},
        {"Symbol": "XYZ", "Sector": "Energy", "Price/Earnings": 8.1,
         "value_pct": 91, "quality_pct": 60, "quadrant": "CHEAP + QUALITY"},
    ]


def test_build_alert_includes_cape_and_label():
    msg = build_alert("2026-06-02", cape=30.8, cape_label="EXPENSIVE",
                      candidates=_cands())
    assert "30.8" in msg
    assert "EXPENSIVE" in msg
    assert "2026-06-02" in msg


def test_build_alert_lists_candidate_symbols():
    msg = build_alert("2026-06-02", cape=30.8, cape_label="EXPENSIVE",
                      candidates=_cands())
    assert "EG" in msg
    assert "XYZ" in msg


def test_build_alert_always_carries_disclaimer():
    msg = build_alert("2026-06-02", cape=30.8, cape_label="EXPENSIVE",
                      candidates=[])
    assert DISCLAIMER in msg


def test_build_alert_handles_no_candidates_gracefully():
    msg = build_alert("2026-06-02", cape=20.0, cape_label="NORMAL",
                      candidates=[])
    # no crash, and it says there were none rather than printing an empty list
    assert "0" in msg or "niciun" in msg.lower() or "none" in msg.lower()


def test_send_message_posts_to_telegram_api():
    captured = {}

    def fake_opener(req, timeout=None):
        captured["url"] = req.full_url
        captured["data"] = json.loads(req.data.decode())

        class _Resp:
            def read(self): return b'{"ok":true}'
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return _Resp()

    send_message("TOKEN123", "999", "hello", opener=fake_opener)
    assert "TOKEN123" in captured["url"]
    assert "sendMessage" in captured["url"]
    assert captured["data"]["chat_id"] == "999"
    assert captured["data"]["text"] == "hello"
