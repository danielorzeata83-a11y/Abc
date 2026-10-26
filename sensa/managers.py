"""Browse every 13F filer by name (A-Z), from the manager list saved with the Smart Money overview."""

_MAX_LIMIT = 200


def letter_of(name):
    """First letter of the name (lower case); digits, symbols and empty names go to '0'."""
    for ch in name or "":
        if ch.isalpha():
            return ch.lower()
        if ch.isdigit():
            return "0"
    return "0"


def browse(managers, letter, offset=0, limit=50, query=None):
    """Page of filers for one letter, or for a name search (which ignores the letter)."""
    if query:
        q = query.strip().lower()
        pool = [x for x in managers if q in x["name"].lower()] if q else []
    elif letter and len(letter) == 1 and (letter.isalpha() or letter == "0"):
        pool = [x for x in managers if letter_of(x["name"]) == letter.lower()]
    else:
        pool = []
    pool = sorted(pool, key=lambda x: x["name"].lower())
    offset = max(0, int(offset))
    limit = max(1, min(int(limit), _MAX_LIMIT))
    return {"letter": letter, "total": len(pool), "aum": sum(x["aum"] for x in pool),
            "avg_entries": round(sum(x["entries"] for x in pool) / len(pool)) if pool else 0,
            "rows": pool[offset:offset + limit]}
