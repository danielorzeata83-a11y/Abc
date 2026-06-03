"""Daily research alert -> Telegram.

Reads the CAPE thermometer + runs the value/quality screener, then pushes the
day's CHEAP+QUALITY candidates to your phone via a Telegram bot. Designed to be
run from cron / Windows Task Scheduler each morning (ideally after update_data.py).

    set TELEGRAM_TOKEN=123:ABC...      (from @BotFather)
    set TELEGRAM_CHAT_ID=999...        (from telegram_chatid.py)
    python telegram_alert.py

Use --dry-run to print the message without sending. Not investment advice.
"""

import argparse
import os

import pandas as pd

from markov.valuation import valuation_label
from markov.screener import compute_scores, QUADRANTS
from markov.telegram import build_alert, send_message


def _DATA(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)


def _env_float(name, default):
    """Read a float env var, tolerating absent/empty values (undefined GitHub
    secrets arrive as an empty string)."""
    try:
        return float(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monthly", default=_DATA("sp500_monthly.csv"),
                    help="Shiller CAPE history CSV")
    ap.add_argument("--financials", default=_DATA("sp500_financials.csv"),
                    help="fundamentals snapshot CSV for the screener")
    ap.add_argument("--token", default=os.environ.get("TELEGRAM_TOKEN"))
    ap.add_argument("--chat-id", default=os.environ.get("TELEGRAM_CHAT_ID"))
    ap.add_argument("--cheap-threshold", type=float,
                    default=_env_float("CHEAP_CAPE_THRESHOLD", 22.0),
                    help="CAPE at/below which a 'be greedy' banner is prepended")
    ap.add_argument("--aggressive-threshold", type=float,
                    default=_env_float("AGGRESSIVE_CAPE_THRESHOLD", 15.0),
                    help="CAPE at/below which a louder 'buy aggressively' banner fires")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the alert instead of sending it")
    args = ap.parse_args()

    # --- CAPE reading ---
    m = pd.read_csv(args.monthly)
    m = m[(m["SP500"] > 0) & (m["PE10"] > 0)]
    cape = float(m["PE10"].to_numpy()[-1])
    label = valuation_label(cape)
    asof = str(m["Date"].to_numpy()[-1])[:10]

    # --- screener: today's CHEAP+QUALITY ---
    raw = pd.read_csv(args.financials)
    scored = compute_scores(raw)
    cq = scored[scored["quadrant"] == QUADRANTS[0]].sort_values(
        "value_pct", ascending=False)
    candidates = cq.to_dict("records")

    msg = build_alert(asof, cape, label, candidates,
                      cheap_threshold=args.cheap_threshold,
                      aggressive_threshold=args.aggressive_threshold)

    if args.dry_run:
        print(msg)
        return
    if not args.token or not args.chat_id:
        raise SystemExit("Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID (env or "
                         "--token/--chat-id). Use --dry-run to preview without "
                         "sending. Get them via @BotFather + telegram_chatid.py.")
    resp = send_message(args.token, args.chat_id, msg)
    print("Sent." if resp.get("ok") else f"Telegram error: {resp}")


if __name__ == "__main__":
    main()
