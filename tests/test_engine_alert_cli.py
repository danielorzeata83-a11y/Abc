"""CLI raport motor: dry-run tipareste, trimiterea foloseste sender injectat."""

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
import engine_alert_cli


def _seed_daily(dirpath, symbol, rets):
    n = len(rets) + 1
    idx = pd.bdate_range("2010-01-04", periods=n)
    close = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + rets)))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def _seed_two(d):
    rng = np.random.default_rng(0)
    for s in ("AAA", "BBB"):
        _seed_daily(d, s, rng.normal(0, 0.01, size=600))


def test_dry_run_prints_without_sending(tmp_path, capsys):
    d = str(tmp_path)
    _seed_two(d)
    sent = []
    engine_alert_cli.main(["--symbols", "AAA,BBB", "--data-dir", d, "--dry-run"],
                          sender=lambda *a: sent.append(a) or {"ok": True})
    out = capsys.readouterr().out
    assert "VOLATILITATE" in out and "LEAD-LAG" in out
    assert sent == []                         # dry-run nu trimite


def test_send_uses_injected_sender(tmp_path, capsys):
    d = str(tmp_path)
    _seed_two(d)
    sent = []

    def fake_sender(token, chat_id, text):
        sent.append((token, chat_id, text))
        return {"ok": True}

    engine_alert_cli.main(["--symbols", "AAA,BBB", "--data-dir", d,
                           "--token", "T", "--chat-id", "C"], sender=fake_sender)
    assert len(sent) == 1 and sent[0][0] == "T" and sent[0][1] == "C"
    assert "consiliere de investi" in sent[0][2].lower()
    assert "Trimis." in capsys.readouterr().out
