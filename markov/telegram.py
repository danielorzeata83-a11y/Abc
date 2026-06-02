"""Telegram alert builder + sender (zero external dependencies).

Builds the daily research alert text from the CAPE reading and the screener's
CHEAP+QUALITY candidates, then sends it via Telegram's Bot API using urllib.
Borrowed idea: a messaging "gateway" that pushes results to your phone -- the
one genuinely useful pattern from agent frameworks for a small retail workflow.

The alert ALWAYS carries the disclaimer. Nothing here is investment advice.
"""

import json
import urllib.request

DISCLAIMER = "NU este consiliere de investitii."


def build_alert(asof, cape, cape_label, candidates):
    """Format the daily alert message.

    candidates: iterable of dicts with Symbol / Sector / Price/Earnings /
    value_pct / quality_pct (as produced by markov.screener.compute_scores).
    """
    lines = [
        f"Abc -- raport {asof}",
        f"CAPE {cape:.1f} ({cape_label})",
        "",
    ]
    cands = list(candidates)
    if not cands:
        lines.append("Niciun candidat CHEAP+QUALITY azi.")
    else:
        lines.append(f"Top value azi ({len(cands)} candidati):")
        for c in cands[:8]:
            lines.append(
                f"- {c['Symbol']} ({c['Sector'][:18]}) "
                f"P/E {c['Price/Earnings']:.1f} | "
                f"val {c['value_pct']:.0f} / qual {c['quality_pct']:.0f}"
            )
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def send_message(token, chat_id, text, opener=None):
    """POST `text` to a Telegram chat. `opener` is injectable for testing."""
    opener = opener or urllib.request.urlopen
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"})
    with opener(req, timeout=30) as resp:
        return json.loads(resp.read().decode())
