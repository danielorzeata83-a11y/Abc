"""Insider (Form 4) open-market trades from SEC's quarterly Insider Transactions Data Sets.

Pure functions over the bulk TSV tables. Only open-market purchases (code P) and sales (code S)
are kept: grants, option exercises and gifts say little about an insider's conviction."""

import re
from datetime import date, timedelta

from sensa.universe import iso_date, read_tsv

_SIDE = {"P": "buy", "S": "sell"}


def _role(owners):
    for _, rel, title in owners:
        if title:
            return title
    rel = owners[0][1] if owners else ""
    return "Director" if "Director" in rel else "Officer" if "Officer" in rel else \
        "10% owner" if "TenPercent" in rel else "Insider"


def load_trades(submission, owners, trans):
    """Open-market Form 4 trades, one row per (filing, day, side); same-day lines are merged."""
    subs = {}
    for r in read_tsv(submission):
        raw = (r.get("ISSUERTRADINGSYMBOL") or "").replace(",", " ").split()
        sym = raw[0].upper() if raw else ""                      # "LEN, LEN.B": the first class
        if r.get("DOCUMENT_TYPE") != "4" or not re.fullmatch(r"[A-Z][A-Z0-9.\-/]{0,9}", sym) or sym in ("NONE", "N/A", "NA"):
            continue
        subs[r["ACCESSION_NUMBER"]] = {"symbol": sym, "issuer": r.get("ISSUERNAME", "").strip(),
                                       "filed": iso_date(r.get("FILING_DATE", "")),
                                       "plan": (r.get("AFF10B5ONE") or "").strip().lower() in ("1", "true", "y")}
    own = {}
    for r in read_tsv(owners):
        if r["ACCESSION_NUMBER"] in subs:
            own.setdefault(r["ACCESSION_NUMBER"], []).append(
                (r.get("RPTOWNERNAME", "").strip(), r.get("RPTOWNER_RELATIONSHIP", ""), r.get("RPTOWNER_TITLE", "").strip()))
    merged = {}
    for r in read_tsv(trans):
        acc, side = r["ACCESSION_NUMBER"], _SIDE.get((r.get("TRANS_CODE") or "").strip())
        if acc not in subs or not side:
            continue
        try:
            shares, price = float(r["TRANS_SHARES"]), float(r["TRANS_PRICEPERSHARE"])
        except ValueError:
            continue
        if shares <= 0 or price <= 0:
            continue
        d = iso_date(r.get("TRANS_DATE", ""))
        if not d:
            continue
        k = (acc, d, side)
        owned = None
        if (r.get("DIRECT_INDIRECT_OWNERSHIP") or "").strip().upper() == "D":
            try:
                owned = float(r.get("SHRSOWNFOLWNG") or "")
            except ValueError:
                owned = None
        m = merged.get(k)
        if m is None:
            s, o = subs[acc], own.get(acc, [])
            merged[k] = {"symbol": s["symbol"], "issuer": s["issuer"], "owner": " / ".join(sorted({n for n, _, _ in o})) or "Unknown",
                         "role": _role(o), "side": side, "shares": shares, "value": shares * price, "date": d,
                         "filed": s["filed"], "accession": acc, "plan": s["plan"], "owned_after": owned}
        else:
            m["shares"] += shares
            m["value"] += shares * price
            if owned is not None:
                m["owned_after"] = owned                      # the last direct line of the day carries the final balance
    # the same trade is often filed once per joint reporting owner: count it once, name everyone
    uniq = {}
    for t in merged.values():
        k = (t["symbol"], t["date"], t["side"], round(t["shares"], 4), round(t["value"] / t["shares"], 4))
        u = uniq.get(k)
        if u is None:
            uniq[k] = t
        else:
            u["owner"] = " / ".join(sorted(set(u["owner"].split(" / ")) | set(t["owner"].split(" / "))))
    out = list(uniq.values())
    for t in out:
        t["price"] = t["value"] / t["shares"]
    return sorted(out, key=lambda t: (t["date"], t["symbol"]))


def aggregate(trades, as_of, days=30, top=10, min_insiders=3, include_plans=True):
    """Top buyers / sellers and cluster buys in the `days` before `as_of` ('YYYY-MM-DD')."""
    end = date.fromisoformat(as_of)
    start = (end - timedelta(days=days)).isoformat()
    win = [t for t in trades if start <= t["date"] <= as_of and (include_plans or not t["plan"] or t["side"] == "buy")]

    def per_insider(side):
        g = {}
        for t in win:
            if t["side"] != side:
                continue
            x = g.setdefault((t["symbol"], t["owner"]), {"symbol": t["symbol"], "issuer": t["issuer"], "owner": t["owner"],
                                                           "role": t["role"], "value": 0.0, "shares": 0.0, "trades": 0,
                                                           "last": t["date"], "plan": t["plan"]})
            x["value"] += t["value"]
            x["shares"] += t["shares"]
            x["trades"] += 1
            x["last"] = max(x["last"], t["date"])
        rows = sorted(g.values(), key=lambda r: r["value"], reverse=True)
        for r in rows:
            r["price"] = r["value"] / r["shares"]
        return rows
    buys, sells = per_insider("buy"), per_insider("sell")
    by_sym = {}
    for t in win:
        if t["side"] == "buy":
            by_sym.setdefault(t["symbol"], []).append(t)
    clusters = []
    for sym, ts in by_sym.items():
        people = {n for t in ts for n in t["owner"].split(" / ")}
        if len(people) >= min_insiders:
            clusters.append({"symbol": sym, "issuer": ts[0]["issuer"], "insiders": len(people), "trades": len(ts),
                             "value": sum(t["value"] for t in ts), "last": max(t["date"] for t in ts),
                             "names": sorted(people)[:6], "roles": sorted({t["role"] for t in ts})[:4]})
    clusters.sort(key=lambda c: (c["insiders"], c["value"]), reverse=True)
    return {"as_of": as_of, "days": days, "trades": len(win),
            "buy_value": sum(t["value"] for t in win if t["side"] == "buy"),
            "sell_value": sum(t["value"] for t in win if t["side"] == "sell"),
            "top_buys": buys[:top], "top_sells": sells[:top], "clusters": clusters[:top]}


# ------------------------------------------------------------------ build / store / serve
import json
import os

from sensa.fsutil import replace_file
import re
from datetime import datetime, timezone

from markov.data_providers import DataUnavailable
from sensa.jobs import BackgroundJob
from sensa.universe import _tables

_SET = re.compile(r'href="(/files/[a-z]+/data/insider-transactions-data-sets/((\d{4})q([1-4]))_form345\.zip)"')


def find_insider_sets(html):
    """Quarterly insider data-set zips listed on SEC's page, newest first."""
    seen, out = set(), []
    for href, quarter, year, q in _SET.findall(html):
        if href not in seen:
            seen.add(href)
            out.append({"quarter": quarter, "label": f"Q{q} {year}", "url": "https://www.sec.gov" + href})
    return sorted(out, key=lambda s: s["quarter"], reverse=True)


def _path(data_dir):
    return os.path.join(data_dir, "insiders.json")


def load_insiders(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        raise DataUnavailable("No insider data yet. Press Update to build it from SEC data.") from None


def refresh_insiders(data_dir, listing_html, download, min_value=5000, force=False, max_member_bytes=3 * 10 ** 9):
    """Build the stored trade list from SEC's newest insider data set; None when already current.
    The stored file is replaced atomically, so a failed build keeps the previous good one."""
    sets = find_insider_sets(listing_html)
    if not sets:
        raise DataUnavailable("no insider data sets found on SEC's page")
    latest = sets[0]
    try:
        stored = load_insiders(data_dir)
    except DataUnavailable:
        stored = None
    if stored and stored.get("quarter_id") == latest["quarter"] and not force:
        return None
    zdir = os.path.join(data_dir, "zips")
    os.makedirs(zdir, exist_ok=True)
    dest = os.path.join(zdir, os.path.basename(latest["url"]))
    if not os.path.exists(dest):
        download(latest["url"], dest + ".part")
        replace_file(dest + ".part", dest)
    z, opener = _tables(dest, max_member_bytes)
    with z:
        trades = load_trades(opener("SUBMISSION.tsv"), opener("REPORTINGOWNER.tsv"), opener("NONDERIV_TRANS.tsv"))
    trades = [t for t in trades if t["value"] >= min_value]
    if not trades:
        raise DataUnavailable("the insider data set contained no open-market trades")
    data = {"quarter": latest["label"], "quarter_id": latest["quarter"], "as_of": max(t["filed"] for t in trades),
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "trades": trades}
    tmp = _path(data_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    os.replace(tmp, _path(data_dir))
    return data


class InsiderService(BackgroundJob):
    def __init__(self, data_dir, fetch_listing, download, min_value=5000):
        super().__init__("downloading and processing the SEC insider data set")
        self.data_dir, self.fetch_listing, self.download, self.min_value = data_dir, fetch_listing, download, min_value
        self._data = None

    def _load(self):
        if self._data is None:
            self._data = load_insiders(self.data_dir)
        return self._data

    def check(self, force=False):
        d = refresh_insiders(self.data_dir, self.fetch_listing(), self.download, self.min_value, force)
        if d is not None:
            self._data = None
        return d

    def trades_since(self, days):
        """Trades in the last `days` before the newest one (for performance work)."""
        d = self._load()
        from datetime import date, timedelta
        if not d["trades"] or days <= 0:
            return []
        end = date.fromisoformat(d["as_of"])
        return [t for t in d["trades"] if t["date"] >= (end - timedelta(days=days)).isoformat()]

    def overview(self, days=30, include_plans=True):
        d = self._load()
        return {"quarter": d["quarter"], "generated": d["generated"],
                **aggregate(d["trades"], d["as_of"], days, include_plans=include_plans)}

    def symbol(self, sym, limit=200):
        d = self._load()
        s = sym.upper()
        ts = sorted((t for t in d["trades"] if t["symbol"] == s), key=lambda t: (t["date"], t["value"]), reverse=True)
        return {"symbol": s, "quarter": d["quarter"], "as_of": d["as_of"], "trades": ts[:limit]}

    def status(self):
        st = self.state()
        try:
            d = self._load()
            st.update(quarter=d["quarter"], built_at=d["generated"], as_of=d["as_of"])
        except DataUnavailable:
            st.update(quarter=None, built_at=None, as_of=None)
        return st
