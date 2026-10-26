"""Build the cross-fund Smart Money overview (top managers, most-held stocks, what moves inside them).

Uses SEC's quarterly Form 13F data sets (free, ~100 MB each; downloaded once, kept in data/smart_money/zips).
Re-running does nothing until SEC publishes a newer quarter, unless --force.

    set SEC_CONTACT=you@example.com
    python smart_money_build.py            # top 100 managers
    python smart_money_build.py --top 50 --force

Research artifact -- NOT investment advice."""

import argparse
import os
import shutil
import sys
import urllib.error
import urllib.request

from markov.data_providers import DataUnavailable
from sensa.providers import http_fetch, http_post
from sensa.thirteenf import Figi
from sensa.universe import refresh_overview

PAGE = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "smart_money")


def make_downloader(contact):
    ua = {"User-Agent": f"Abc-dashboard-research/1.0 {contact}"}

    def download(url, dest):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=120) as r, open(dest, "wb") as fh:
                shutil.copyfileobj(r, fh, 1 << 20)
        except (urllib.error.URLError, OSError) as e:
            raise DataUnavailable(f"download failed ({type(e).__name__}) for {url.rsplit('/', 1)[-1]}") from e
    return download


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--top", type=int, default=100, help="how many of the largest managers to include")
    ap.add_argument("--force", action="store_true", help="rebuild even if the latest quarter is already built")
    ap.add_argument("--data-dir", default=DATA_DIR)
    a = ap.parse_args(argv)
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("Set SEC_CONTACT (SEC requires a contact in the User-Agent).", file=sys.stderr)
        return 2
    figi = Figi(http_post, min_interval=2.5, cache_path=os.path.join(a.data_dir, "figi.json"))
    try:
        listing = http_fetch(PAGE, {"User-Agent": f"Abc-dashboard-research/1.0 {contact}"})
        o = refresh_overview(a.data_dir, listing, make_downloader(contact), figi, top=a.top, force=a.force)
    except DataUnavailable as e:
        print(f"Build failed: {e}", file=sys.stderr)
        return 1
    print("Already up to date." if o is None else
          f"Built {o['quarter']} vs {o['prev_quarter']}: {o['cohort']} managers, ${o['total_aum'] / 1e12:.2f}T, "
          f"{len(o['stocks'])} stocks kept ({o['distinct_stocks']} distinct).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
