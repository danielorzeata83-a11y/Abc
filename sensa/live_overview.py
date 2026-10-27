"""Smart Money for the quarter that is still being reported.

Takes the top-100 funds of the last complete quarter, keeps those that have already filed the next quarter's
13F (read live from EDGAR) and compares each with its own previous quarter, using the same maths as the
complete overview. As more funds report the view fills up; once SEC publishes the bulk data set, the
complete overview takes over."""

import sqlite3

from markov.data_providers import DataUnavailable
from sensa.holders import _uri
from sensa.live13f import LiveStore, next_quarter_end
from sensa.thirteenf import quarter_label
from sensa.universe import assemble_overview


def build_live_overview(bulk, holders_db, live_db, figi=None):
    cohort = {f["cik"]: f for f in bulk["funds"]}
    store = LiveStore(live_db)
    reported = [f for f in store.filers() if f["cik"] in cohort and f["period"] > bulk["period"]]
    if not reported:
        raise DataUnavailable(f"No top-{len(cohort)} fund has filed its {quarter_label(next_quarter_end(bulk['period']))} report yet")
    period = max(f["period"] for f in reported)
    reported = [f for f in reported if f["period"] == period]
    ciks = [f["cik"] for f in reported]
    cur_h = store.share_holdings(ciks)
    managers = sorted(({"cik": f["cik"], "name": f["name"], "state": cohort[f["cik"]].get("state", ""),
                        "accession": f["accession"], "filed": f["filed"], "form": f["form"], "aum": f["aum"],
                        "entries": len(cur_h.get(f["cik"], []))} for f in reported), key=lambda m: m["aum"], reverse=True)
    con = sqlite3.connect(_uri(holders_db), uri=True)
    try:
        issuers = dict(con.execute("SELECT cusip, issuer FROM iss"))
        prev_h = {}
        for cik in ciks:
            rows = con.execute("SELECT cusip, shares, value FROM h WHERE q = 0 AND cik = ? AND kind = 'SH'", (cik,)).fetchall()
            if rows:
                prev_h[cik] = [{"cusip": c, "issuer": issuers.get(c, ""), "value": v, "shares": s} for c, s, v in rows]
    finally:
        con.close()
    prev_managers = {c: {"aum": cohort[c]["aum"]} for c in ciks}
    o = assemble_overview(managers, cur_h, prev_h, prev_managers, period, bulk["period"], figi)
    o["live"] = {"reported": len(managers), "of": len(cohort)}
    return o


def _live_path(data_dir):
    import os
    return os.path.join(data_dir, "overview_live.json")


def refresh_live_overview(data_dir, figi=None):
    """Rebuild overview_live.json from what has been read so far. True when a view exists, False when no top fund
    has reported yet (a stale file is removed)."""
    import json
    import os
    from sensa.universe import _write_json, load_overview
    bulk = load_overview(data_dir)
    try:
        o = build_live_overview(bulk, os.path.join(data_dir, "holders.db"), os.path.join(data_dir, "live13f.db"), figi)
    except DataUnavailable:
        try:
            os.remove(_live_path(data_dir))
        except OSError:
            pass
        return False
    _write_json(_live_path(data_dir), o)
    return True


def load_live_overview(data_dir):
    import json
    from sensa.universe import load_overview
    try:
        with open(_live_path(data_dir), encoding="utf-8") as fh:
            o = json.load(fh)
        if o.get("prev_period") == load_overview(data_dir)["period"]:
            return o
    except (OSError, ValueError, KeyError):
        pass
    raise DataUnavailable("No live view yet. It appears as soon as a top-100 fund files its next-quarter 13F; "
                          "press Update on the Smart Money page if the quarter data set is old.")
