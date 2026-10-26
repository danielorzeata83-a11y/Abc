"""FINRA daily consolidated short-sale volume (free, no key, published after close).
This is short *volume* (share of the day's trades that were short sales), not
short interest and not dark-pool prints."""

from datetime import timedelta

from markov.data_providers import DataUnavailable

URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{ymd}.txt"


class Finra:
    def __init__(self, fetch):
        self.fetch = fetch

    def load(self, today, lookback=7):
        for back in range(lookback + 1):
            day = today - timedelta(days=back)
            try:
                text = self.fetch(URL.format(ymd=day.strftime("%Y%m%d")), {})
            except DataUnavailable:
                continue        # weekend / holiday / not yet published
            rows = {}
            for line in text.splitlines()[1:]:
                p = line.split("|")
                if len(p) >= 5:
                    try:
                        rows[p[1]] = (float(p[2]), float(p[4]))
                    except ValueError:
                        continue
            return {"date": day.isoformat(), "rows": rows}
        raise DataUnavailable("no FINRA short-volume file in the last %d days" % lookback)

    @staticmethod
    def lookup(data, symbol):
        sv = data["rows"].get(symbol.upper())
        if sv is None:
            return None
        short, total = sv
        return {"symbol": symbol.upper(), "date": data["date"], "short_volume": short,
                "total_volume": total, "short_ratio": round(short / total, 4) if total else None}
