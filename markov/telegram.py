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


def cheap_market_banner(cape, threshold=22.0):
    """A prominent 'be greedy' banner, only when the market has gotten cheap.

    Returns "" when CAPE is above `threshold` (the common case -- stays quiet).
    Below the threshold the market is attractively priced; below 15 it is
    historically cheap (rare), so the message is louder. Not investment advice.
    """
    if not (cape <= threshold):
        return ""
    if cape <= 15:
        return (f">>> PIATA E FOARTE IEFTINA <<<\n"
                f"CAPE {cape:.1f} -- nivel rar istoric (sub 15).\n"
                f"Be greedy when others are fearful.")
    return (f">>> PIATA A DEVENIT IEFTINA <<<\n"
            f"CAPE {cape:.1f} (sub pragul {threshold:.0f}).\n"
            f"Be greedy when others are fearful.")


def build_alert(asof, cape, cape_label, candidates, cheap_threshold=22.0):
    """Format the daily alert message.

    candidates: iterable of dicts with Symbol / Sector / Price/Earnings /
    value_pct / quality_pct (as produced by markov.screener.compute_scores).
    A 'be greedy' banner is prepended when CAPE <= cheap_threshold.
    """
    lines = []
    banner = cheap_market_banner(cape, cheap_threshold)
    if banner:
        lines += [banner, ""]
    lines += [
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
