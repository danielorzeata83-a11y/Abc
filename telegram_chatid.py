"""One-time helper: find YOUR Telegram chat_id.

Steps:
  1. In Telegram, create a bot with @BotFather -> /newbot -> copy the TOKEN.
  2. Send any message (e.g. "hi") to your new bot.
  3. Run:  python telegram_chatid.py --token YOUR_TOKEN
     It prints the chat_id you should put in your .env.

Reads the bot's getUpdates feed; no message sent. Not investment advice.
"""

import argparse
import json
import os
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("TELEGRAM_TOKEN"),
                    help="bot token from @BotFather (or set TELEGRAM_TOKEN)")
    args = ap.parse_args()
    if not args.token:
        raise SystemExit("Pass --token YOUR_TOKEN (or set TELEGRAM_TOKEN). "
                         "Get it from @BotFather with /newbot.")

    url = f"https://api.telegram.org/bot{args.token}/getUpdates"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    if not data.get("ok"):
        raise SystemExit(f"Telegram error: {data}")
    results = data.get("result", [])
    if not results:
        raise SystemExit("No messages found. Send a message TO your bot first, "
                         "then run this again.")

    seen = {}
    for upd in results:
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat", {})
        if "id" in chat:
            seen[chat["id"]] = chat.get("first_name") or chat.get("title") or ""
    print("Chat(s) that messaged your bot:")
    for cid, name in seen.items():
        print(f"  chat_id = {cid}   ({name})")
    print("\nPut the chat_id into your .env as TELEGRAM_CHAT_ID=...")


if __name__ == "__main__":
    main()
