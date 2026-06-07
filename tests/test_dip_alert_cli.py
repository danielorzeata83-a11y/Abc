"""Smoke pentru dip_alert_cli: dry-run tipareste, sender injectat primeste textul,
quiet-if-empty nu trimite cand nu e nimic. Fara retea (sender fals)."""

import numpy as np
import pandas as pd

import dip_alert_cli as cli


def _universe(tmp_path):
    csv = tmp_path / "u.csv"
    # FALL: cade 45% de la maxim -> dip adanc; TOP: urca mereu
    fall = np.concatenate([np.linspace(50, 100, 80), np.linspace(100, 55, 20)])
    top = np.arange(1, 101, dtype=float)
    rows = []
    for name, ser in [("FALL", fall), ("TOP", top)]:
        for d, c in zip(pd.bdate_range("2015-01-02", periods=len(ser)).astype(str), ser):
            rows.append({"date": d, "open": c, "high": c, "low": c, "close": c,
                         "volume": 1e6, "Name": name})
    pd.DataFrame(rows).to_csv(csv, index=False)
    return str(csv)


def test_dry_run_prints_without_sending(tmp_path, capsys):
    sent = []
    rc = cli.main(["--watchlist", "FALL,TOP", "--universe", _universe(tmp_path),
                   "--dry-run"], sender=lambda *a: sent.append(a))
    assert rc == 0 and sent == []
    assert "dip-adanc" in capsys.readouterr().out


def test_sender_receives_text(tmp_path):
    sent = []
    cli.main(["--watchlist", "FALL,TOP", "--universe", _universe(tmp_path),
              "--token", "T", "--chat-id", "C"],
             sender=lambda tok, chat, text: sent.append((tok, chat, text)))
    assert len(sent) == 1 and sent[0][0] == "T"
    assert "FALL" in sent[0][2]


def test_quiet_if_empty_skips_send(tmp_path):
    sent = []
    rc = cli.main(["--watchlist", "TOP", "--universe", _universe(tmp_path),
                   "--token", "T", "--chat-id", "C", "--quiet-if-empty"],
                  sender=lambda *a: sent.append(a))
    assert rc == 0 and sent == []          # TOP nu e in dip -> nimic trimis
