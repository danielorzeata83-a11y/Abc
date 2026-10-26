"""Cross-fund view of the biggest 13F managers, built from SEC's bulk Form 13F data sets
(quarterly zips with SUBMISSION / COVERPAGE / SUMMARYPAGE / INFOTABLE tables).

Pure functions over text streams, so they are testable without the 400 MB files."""

import csv

_MONTHS = {m: i + 1 for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"))}


def iso_date(s):
    """'14-AUG-2026' -> '2026-08-14' (locale independent). Returns '' if unparsable."""
    try:
        d, m, y = s.strip().upper().split("-")
        return f"{int(y):04d}-{_MONTHS[m]:02d}-{int(d):02d}"
    except (ValueError, KeyError):
        return ""


def read_tsv(fh):
    """Yield one dict per row of a SEC bulk TSV (no quoting: quotes inside names are literal)."""
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    head = next(rd, None)
    if not head:
        return
    for row in rd:
        if len(row) < len(head):
            row = row + [""] * (len(head) - len(row))
        yield dict(zip(head, row))


def select_managers(submission, coverpage, summary, period, top=None):
    """Managers with a holdings report for `period` ('YYYY-MM-DD'), ranked by reported value.

    Per manager: the latest RESTATEMENT amendment if one exists, else the original 13F-HR.
    Amendments that only add holdings and 13F notices (no holdings of their own) are not used."""
    cover = {r["ACCESSION_NUMBER"]: r for r in read_tsv(coverpage)}
    summ = {r["ACCESSION_NUMBER"]: r for r in read_tsv(summary)}
    best = {}
    for s in read_tsv(submission):
        if s["SUBMISSIONTYPE"] not in ("13F-HR", "13F-HR/A") or iso_date(s["PERIODOFREPORT"]) != period:
            continue
        acc = s["ACCESSION_NUMBER"]
        c, sm = cover.get(acc), summ.get(acc)
        if not c or not sm or "NOTICE" in c.get("REPORTTYPE", "").upper():
            continue
        restated = c.get("ISAMENDMENT") == "Y" and c.get("AMENDMENTTYPE", "").upper() == "RESTATEMENT"
        original = s["SUBMISSIONTYPE"] == "13F-HR"
        if not (restated or original):
            continue
        try:
            aum, entries = float(sm["TABLEVALUETOTAL"]), int(sm["TABLEENTRYTOTAL"])
        except ValueError:
            continue
        filed = iso_date(s["FILING_DATE"])
        cand = {"cik": s["CIK"], "name": c["FILINGMANAGER_NAME"].strip(), "state": c["FILINGMANAGER_STATEORCOUNTRY"],
                "accession": acc, "filed": filed, "form": s["SUBMISSIONTYPE"], "aum": aum, "entries": entries}
        rank = (restated, filed)                       # restatement beats original; later beats earlier
        cur = best.get(s["CIK"])
        if cur is None or rank > cur[0]:
            best[s["CIK"]] = (rank, cand)
    ms = sorted((v[1] for v in best.values()), key=lambda m: m["aum"], reverse=True)
    return ms[:top] if top else ms


def load_holdings(infotable, accession_to_cik):
    """Stream INFOTABLE and keep plain-share holdings of the wanted filings, merged by CUSIP.

    Options (PUT/CALL) and bond principal (PRN) are not 'held shares' and are left out."""
    acc = set(accession_to_cik)
    out = {}
    for r in read_tsv(infotable):
        a = r["ACCESSION_NUMBER"]
        if a not in acc or r.get("PUTCALL", "").strip() or r.get("SSHPRNAMTTYPE", "").strip().upper() != "SH":
            continue
        try:
            value, shares = float(r["VALUE"]), float(r["SSHPRNAMT"])
        except ValueError:
            continue
        by = out.setdefault(accession_to_cik[a], {})
        h = by.get(r["CUSIP"])
        if h is None:
            by[r["CUSIP"]] = {"cusip": r["CUSIP"], "issuer": r["NAMEOFISSUER"].strip(), "value": value, "shares": shares}
        else:
            h["value"] += value
            h["shares"] += shares
    return {cik: list(by.values()) for cik, by in out.items()}


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _scaling(cur, prev):
    """A fund's uniform share growth (inflows/outflows): median share ratio over continuing positions."""
    r = [cur[c] / prev[c] for c in cur.keys() & prev.keys() if cur[c] > 0 and prev[c] > 0]
    return _median(r) if r else 1.0


_SPLITS = (1 / 100, 1 / 50, 1 / 40, 1 / 25, 1 / 20, 1 / 15, 1 / 10, 1 / 8, 1 / 5, 1 / 4, 1 / 3, 1 / 2, 1.5, 2, 3, 4,
           5, 6, 7, 8, 10, 15, 20, 25, 30, 40, 50, 100)


def split_factors(current, previous, min_funds=5, band=0.25, min_agree=0.6, snap=0.08):
    """Stocks whose share count moved by a standard split ratio at most funds: splits, not trading.

    The median fund ratio must sit within `snap` of a usual split ratio (2:1, 10:1, 1:10 ...) and at
    least `min_agree` of the funds within +/-`band` of it (funds also trade around the split)."""
    ratios = {}
    for cik in current.keys() & previous.keys():
        cur = {r["cusip"]: r["shares"] for r in current[cik]}
        prv = {r["cusip"]: r["shares"] for r in previous[cik]}
        for c in cur.keys() & prv.keys():
            if cur[c] > 0 and prv[c] > 0:
                ratios.setdefault(c, []).append(cur[c] / prv[c])
    out = {}
    for cusip, rs in ratios.items():
        if len(rs) < min_funds:
            continue
        med = _median(rs)
        if 0.7 < med < 1.4:
            continue
        k = min(_SPLITS, key=lambda x: abs(med / x - 1))
        if abs(med / k - 1) > snap:
            continue
        if sum(1 for r in rs if abs(r / k - 1) <= band) / len(rs) >= min_agree:
            out[cusip] = float(k)
    return out


def adjust_previous(previous, factors):
    """Previous-quarter holdings restated on the current share basis (split-adjusted)."""
    return {cik: [{**r, "shares": r["shares"] * factors[r["cusip"]]} if r["cusip"] in factors else dict(r)
                  for r in rows] for cik, rows in previous.items()}


def aggregate_stocks(current, previous):
    """Cross-fund view per CUSIP. `current` / `previous`: {cik: [holding rows]}.

    holders / value / avg_weight describe this quarter across all funds. Flows (added, reduced,
    new, exited, net_shares, net_flow) use only funds present in BOTH quarters, so a fund that
    skipped a filing cannot look like a mass sale."""
    comparable = set(current) & set(previous)
    st = {}

    def get(cusip, issuer):
        return st.setdefault(cusip, {"cusip": cusip, "issuer": issuer, "holders": 0, "holders_prev": 0,
                                     "value": 0.0, "value_prev": 0.0, "shares": 0.0, "shares_prev": 0.0,
                                     "weights": [], "added": 0, "reduced": 0, "new": 0, "exited": 0,
                                     "net_shares": 0.0, "active_shares": 0.0})
    for cik, rows in current.items():
        total = sum(r["value"] for r in rows) or 1.0
        for r in rows:
            s = get(r["cusip"], r["issuer"])
            s["holders"] += 1
            s["value"] += r["value"]
            s["shares"] += r["shares"]
            s["weights"].append(r["value"] / total * 100)
    for cik in comparable:
        cur = {r["cusip"]: r for r in current[cik]}
        prev = {r["cusip"]: r for r in previous[cik]}
        g = _scaling({c: r["shares"] for c, r in cur.items()}, {c: r["shares"] for c, r in prev.items()})
        for cusip in cur.keys() | prev.keys():
            c, p = cur.get(cusip), prev.get(cusip)
            s = get(cusip, (c or p)["issuer"])
            if p:
                s["holders_prev"] += 1
                s["value_prev"] += p["value"]
                s["shares_prev"] += p["shares"]
            now_sh, prev_sh = (c["shares"] if c else 0.0), (p["shares"] if p else 0.0)
            s["net_shares"] += now_sh - prev_sh
            s["active_shares"] += now_sh - prev_sh * g          # beyond the fund's own uniform scaling
            if c and not p:
                s["new"] += 1
            elif p and not c:
                s["exited"] += 1
            elif now_sh > prev_sh:
                s["added"] += 1
            elif now_sh < prev_sh:
                s["reduced"] += 1
    out = []
    for s in st.values():
        w = s.pop("weights")
        s["avg_weight"] = sum(w) / len(w) if w else 0.0
        if s["shares"]:
            ref = s["value"] / s["shares"]                 # end-of-quarter price implied by the filings
        else:
            ref = s["value_prev"] / s["shares_prev"] if s["shares_prev"] else 0.0
        s["net_flow"] = s["net_shares"] * ref
        s["active_flow"] = s["active_shares"] * ref
        # corporate actions, not conviction: a name nearly everyone dropped (takeover, delisting) and one that
        # suddenly appears at many funds (IPO, spin-off, CUSIP/ticker change)
        s["gone"] = s["holders_prev"] >= 5 and s["holders"] <= 0.1 * s["holders_prev"]
        s["new_listing"] = s["holders"] >= 20 and s["holders_prev"] <= 0.1 * s["holders"]
        out.append(s)
    return sorted(out, key=lambda s: (s["holders"], s["value"]), reverse=True)


def rank_funds(managers, current, previous_managers, previous):
    """League table of the cohort. `managers` is already ranked; `previous_managers` maps cik -> its
    report for the prior quarter. Equity-only measures (positions, top10, turnover) use plain shares."""
    out = []
    for i, m in enumerate(managers, 1):
        rows = sorted(current.get(m["cik"], []), key=lambda r: r["value"], reverse=True)
        total = sum(r["value"] for r in rows)
        top = [{"cusip": r["cusip"], "issuer": r["issuer"], "value": r["value"],
                "weight": round(r["value"] / total * 100, 2)} for r in rows[:10]] if total else []
        pm = previous_managers.get(m["cik"])
        aum_prev = pm["aum"] if pm else None
        change = round((m["aum"] - aum_prev) / aum_prev * 100, 2) if aum_prev else None
        new = exited = turnover = None
        if m["cik"] in previous and m["cik"] in current:
            cur = {r["cusip"]: r for r in rows}
            prv = {r["cusip"]: r for r in previous[m["cik"]]}
            g = _scaling({c: r["shares"] for c, r in cur.items()}, {c: r["shares"] for c, r in prv.items()})
            new = sum(1 for c in cur if c not in prv)
            exited = sum(1 for c in prv if c not in cur)

            def price(c):                                   # one end-of-quarter price so only trading moves weights
                r = cur.get(c) or prv[c]
                return r["value"] / r["shares"] if r["shares"] else 0.0
            wn = {c: cur[c]["shares"] * price(c) for c in cur}
            wp = {c: prv[c]["shares"] * g * price(c) for c in prv}
            tn, tp = sum(wn.values()), sum(wp.values())
            if tn and tp:
                turnover = round(50 * sum(abs(wn.get(c, 0.0) / tn - wp.get(c, 0.0) / tp) for c in wn.keys() | wp.keys()), 2)
            else:
                turnover = None
        out.append({"rank": i, "cik": m["cik"], "name": m["name"], "state": m["state"], "accession": m["accession"],
                    "filed": m["filed"], "aum": m["aum"], "aum_prev": aum_prev, "aum_change_pct": change,
                    "positions": len(rows), "top": top,
                    "top10_pct": round(sum(t["weight"] for t in top), 2) if total else 0.0,
                    "new": new, "exited": exited, "turnover_pct": turnover})
    return out


import io
import re
import zipfile
from datetime import datetime, timezone

from markov.data_providers import DataUnavailable
from sensa.thirteenf import quarter_label

_MAX_MEMBER = 3 * 10 ** 9      # refuse absurd archive members (zip-bomb guard); real INFOTABLE is ~0.4 GB
_WINDOW = re.compile(r"(\d{2})([a-z]{3})(\d{4})-(\d{2})([a-z]{3})(\d{4})")
_HREF = re.compile(r'href="(/files/[a-z]+/data/form-13f-data-sets/'
                   r'(\d{2}[a-z]{3}\d{4}-\d{2}[a-z]{3}\d{4})_form13f\.zip)"')


def _date(d, mon, y):
    return datetime(int(y), _MONTHS[mon.upper()], int(d))


def quarter_end_in_window(window):
    """'01jun2026-31aug2026' -> '2026-06-30': the quarter whose reports the data set mostly contains."""
    m = _WINDOW.fullmatch(window)
    if not m:
        raise ValueError(f"bad window {window!r}")
    start, end = _date(*m.group(1, 2, 3)), _date(*m.group(4, 5, 6))
    for y in (start.year - 1, start.year):
        for mm, dd in ((3, 31), (6, 30), (9, 30), (12, 31)):
            q = datetime(y, mm, dd)
            if start <= q <= end:
                return q.strftime("%Y-%m-%d")
    raise ValueError(f"no quarter end inside {window!r}")


def find_data_sets(html):
    """Quarterly Form 13F data-set zips listed on SEC's page, newest first."""
    seen, out = set(), []
    for href, window in _HREF.findall(html):
        if href in seen:
            continue
        seen.add(href)
        try:
            period = quarter_end_in_window(window)
        except ValueError:
            continue                        # e.g. the 2024 transition windows hold no quarter end
        out.append({"period": period, "window": window, "url": "https://www.sec.gov" + href})
    return sorted(out, key=lambda s: s["period"], reverse=True)


def _member(z, name, max_bytes):
    info = z.getinfo(name)
    if info.file_size > max_bytes:
        raise DataUnavailable(f"{name} is too large ({info.file_size} bytes)")
    return io.TextIOWrapper(z.open(info), encoding="utf-8", errors="replace", newline="")


def _tables(path, max_bytes):
    z = zipfile.ZipFile(path)
    return z, (lambda n: _member(z, n, max_bytes))


def build_overview(cur_zip, prev_zip, period, prev_period, top=100, figi=None,
                   stocks_limit=300, flows_limit=100, max_member_bytes=_MAX_MEMBER, all_managers=None):
    """The cross-fund overview for the `top` biggest managers of `period`, compared with `prev_period`."""
    zc, oc = _tables(cur_zip, max_member_bytes)
    zp, op = _tables(prev_zip, max_member_bytes)
    with zc, zp:
        everyone = select_managers(oc("SUBMISSION.tsv"), oc("COVERPAGE.tsv"), oc("SUMMARYPAGE.tsv"), period)
        if not everyone:
            raise DataUnavailable(f"no 13F reports for {period} in {cur_zip}")
        managers = everyone[:top]
        if all_managers is not None:
            all_managers.extend({**m, "quarter": quarter_label(period)} for m in everyone)
        prev_managers = {m["cik"]: m for m in
                         select_managers(op("SUBMISSION.tsv"), op("COVERPAGE.tsv"), op("SUMMARYPAGE.tsv"), prev_period)}
        cur_h = load_holdings(oc("INFOTABLE.tsv"), {m["accession"]: m["cik"] for m in managers})
        prev_h = load_holdings(op("INFOTABLE.tsv"), {prev_managers[m["cik"]]["accession"]: m["cik"]
                                                      for m in managers if m["cik"] in prev_managers})
    factors = split_factors(cur_h, prev_h)
    prev_h = adjust_previous(prev_h, factors)                 # restate last quarter after splits
    stocks = aggregate_stocks(cur_h, prev_h)
    funds = rank_funds(managers, cur_h, prev_managers, prev_h)
    names = {s["cusip"]: s["issuer"] for s in stocks}
    by_flow = sorted(stocks, key=lambda s: s["net_flow"])
    keep = {s["cusip"]: s for s in (stocks[:stocks_limit] + by_flow[:flows_limit] + by_flow[-flows_limit:] +
                                    sorted(stocks, key=lambda s: s["new"], reverse=True)[:50] +
                                    sorted(stocks, key=lambda s: s["exited"], reverse=True)[:50])}
    fund_cusips = {t["cusip"] for f in funds for t in f["top"][:3]}
    info = figi.info(sorted(set(keep) | fund_cusips)) if figi else {}
    for s in keep.values():
        i = info.get(s["cusip"]) or {}
        s["ticker"] = i.get("ticker") or s["issuer"][:12].strip()
        s["kind"] = i.get("kind") or "unknown"
    for f in funds:
        f["top"] = [{**t, "ticker": (info.get(t["cusip"]) or {}).get("ticker") or t["issuer"][:12].strip()}
                    for t in f["top"][:10]]
    return {"period": period, "prev_period": prev_period, "quarter": quarter_label(period),
            "prev_quarter": quarter_label(prev_period), "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cohort": len(managers), "comparable": len(set(cur_h) & set(prev_h)),
            "total_aum": sum(m["aum"] for m in managers), "distinct_stocks": len(stocks),
            "splits": [{"cusip": c, "factor": round(f, 4), "issuer": names.get(c, "")} for c, f in sorted(factors.items())],
            "funds": funds, "stocks": sorted(keep.values(), key=lambda s: (s["holders"], s["value"]), reverse=True)}


import json
import os


def _overview_path(data_dir):
    return os.path.join(data_dir, "overview.json")


def load_overview(data_dir):
    try:
        with open(_overview_path(data_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        raise DataUnavailable("no Smart Money overview yet: run `python smart_money_build.py`") from None


def refresh_overview(data_dir, listing_html, download, figi, top=100, force=False):
    """Build (or rebuild) the overview from SEC's two newest quarterly data sets.

    Returns the new overview, or None when the stored one is already for the latest quarter.
    The stored file is replaced atomically, so a failed build keeps the previous good one."""
    sets = find_data_sets(listing_html)
    if len(sets) < 2:
        raise DataUnavailable("need the two newest Form 13F data sets, found fewer")
    cur, prev = sets[0], sets[1]
    try:
        stored = load_overview(data_dir)
    except DataUnavailable:
        stored = None
    if stored and stored.get("period") == cur["period"] and not force:
        return None
    zdir = os.path.join(data_dir, "zips")
    os.makedirs(zdir, exist_ok=True)
    paths = []
    for s in (cur, prev):
        dest = os.path.join(zdir, os.path.basename(s["url"]))
        if not os.path.exists(dest):
            tmp = dest + ".part"
            download(s["url"], tmp)
            os.replace(tmp, dest)
        paths.append(dest)
    everyone = []
    overview = build_overview(paths[0], paths[1], cur["period"], prev["period"], top=top, figi=figi,
                              all_managers=everyone)
    _write_json(os.path.join(data_dir, "managers.json"), everyone)
    tmp = _overview_path(data_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(overview, fh)
    os.replace(tmp, _overview_path(data_dir))
    return overview


def _write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def load_managers(data_dir):
    try:
        with open(os.path.join(data_dir, "managers.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        raise DataUnavailable("No manager list yet. Press Update on the Smart Money page to build it.") from None
