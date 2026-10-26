"""Who holds a stock: an index of every 13F filer's positions, from SEC's bulk Form 13F data sets.

Built once per quarter into one SQLite file (~200 MB). Two quarters are kept so each holder's change can be
shown. Option positions (calls / puts on the stock) are kept apart from the shares themselves."""

import os
import sqlite3
import zipfile
from datetime import datetime, timezone

from markov.data_providers import DataUnavailable
from sensa.universe import _MAX_MEMBER, _tables, read_tsv, select_managers

_SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE filers(q INTEGER, cik TEXT, name TEXT, accession TEXT, filed TEXT, form TEXT, aum REAL, PRIMARY KEY(q, cik));
CREATE TABLE raw(q INTEGER, cik TEXT, cusip TEXT, kind TEXT, shares REAL, value REAL);
CREATE TABLE h(q INTEGER, cik TEXT, cusip TEXT, kind TEXT, shares REAL, value REAL);
CREATE TABLE iss(cusip TEXT PRIMARY KEY, issuer TEXT);
"""


def _load_quarter(con, q, zip_path, period, max_bytes):
    try:
        z, op = _tables(zip_path, max_bytes)
    except (zipfile.BadZipFile, OSError) as e:
        raise DataUnavailable(f"cannot read {os.path.basename(zip_path)} ({type(e).__name__})") from None
    with z:
        try:
            filers = select_managers(op("SUBMISSION.tsv"), op("COVERPAGE.tsv"), op("SUMMARYPAGE.tsv"), period)
        except KeyError as e:
            raise DataUnavailable(f"{os.path.basename(zip_path)} is missing {e}") from None
        if not filers:
            raise DataUnavailable(f"no 13F reports for {period} in {os.path.basename(zip_path)}")
        con.executemany("INSERT INTO filers VALUES(?,?,?,?,?,?,?)",
                        [(q, f["cik"], f["name"], f["accession"], f["filed"], f["form"], f["aum"]) for f in filers])
        acc = {f["accession"]: f["cik"] for f in filers}
        batch, names = [], {}
        for r in read_tsv(op("INFOTABLE.tsv")):
            a = r["ACCESSION_NUMBER"]
            if a not in acc or (r.get("SSHPRNAMTTYPE") or "").strip().upper() != "SH":
                continue                                         # bond principal is not a share holding
            try:
                value, shares = float(r["VALUE"]), float(r["SSHPRNAMT"])
            except ValueError:
                continue
            pc = (r.get("PUTCALL") or "").strip().upper()
            kind = pc if pc in ("CALL", "PUT") else "SH"
            batch.append((q, acc[a], r["CUSIP"], kind, shares, value))
            names.setdefault(r["CUSIP"], (r.get("NAMEOFISSUER") or "").strip().upper())
            if len(batch) >= 200_000:
                con.executemany("INSERT INTO raw VALUES(?,?,?,?,?,?)", batch)
                batch = []
        if batch:
            con.executemany("INSERT INTO raw VALUES(?,?,?,?,?,?)", batch)
        con.executemany("INSERT OR IGNORE INTO iss VALUES(?,?)", names.items())


def build_holders_db(cur_zip, prev_zip, period, prev_period, db_path, max_member_bytes=_MAX_MEMBER):
    """Build the index next to `db_path` and swap it in atomically; a failed build keeps the old file."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    tmp = db_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    try:
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.executescript(_SCHEMA)
        _load_quarter(con, 0, cur_zip, period, max_member_bytes)
        _load_quarter(con, 1, prev_zip, prev_period, max_member_bytes)
        con.execute("INSERT INTO h SELECT q, cik, cusip, kind, SUM(shares), SUM(value) FROM raw GROUP BY q, cik, cusip, kind")
        con.execute("DROP TABLE raw")
        con.execute("CREATE INDEX h_cusip ON h(cusip, q)")
        con.executemany("INSERT INTO meta VALUES(?,?)", [
            ("period", period), ("prev_period", prev_period),
            ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))])
        con.commit()
        con.execute("VACUUM")
        con.close()
        os.replace(tmp, db_path)
    except BaseException:
        con.close()
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _uri(path):
    from pathlib import Path
    return Path(path).resolve().as_uri() + "?mode=ro"


def _connect(db_path):
    if not os.path.exists(db_path):
        raise DataUnavailable("No investor index yet. Press Update on the Smart Money page to build it.")
    return sqlite3.connect(_uri(db_path), uri=True)


def _attach_live(con, live_db):
    """Attach the live (newer-quarter) store as `lv` when it exists and has reports; True when attached."""
    if not live_db or not os.path.exists(live_db):
        return False
    con.execute("ATTACH DATABASE ? AS lv", (_uri(live_db),))
    return con.execute("SELECT count(*) FROM lv.filers").fetchone()[0] > 0


def meta(db_path):
    con = _connect(db_path)
    try:
        return dict(con.execute("SELECT key, value FROM meta").fetchall())
    finally:
        con.close()


def live_meta(live_db, bulk_period):
    """{'period', 'filers'} of reports newer than the bulk data set, or None."""
    if not live_db or not os.path.exists(live_db):
        return None
    con = sqlite3.connect(_uri(live_db), uri=True)
    try:
        r = con.execute("SELECT max(period), count(*) FROM filers WHERE period > ?", (bulk_period,)).fetchone()
    finally:
        con.close()
    return {"period": r[0], "filers": r[1]} if r and r[1] else None


def holders_for_cusip(db_path, cusip, live_db=None):
    """Current holders of a security with the previous quarter's shares, plus their option positions.

    With a live store, filers that already reported the newer quarter use that report (the bulk quarter becomes
    their 'previous'); the others are carried from the bulk quarter. `hist` is [(shares, value, reported)] for
    the bulk previous quarter, the bulk quarter and the live quarter."""
    con = _connect(db_path)
    try:
        cur = con.execute("""SELECT f.cik, f.name, f.accession, f.filed, f.form, f.aum, h.kind, h.shares, h.value
                             FROM h JOIN filers f ON f.q = h.q AND f.cik = h.cik WHERE h.cusip = ? AND h.q = 0""", (cusip,)).fetchall()
        prev = {cik: (sh, val) for cik, sh, val in
                con.execute("SELECT cik, shares, value FROM h WHERE cusip = ? AND q = 1 AND kind = 'SH'", (cusip,))}
        prev_filed = {r[0] for r in con.execute("SELECT cik FROM filers WHERE q = 1")}
        live = {}
        if _attach_live(con, live_db):
            live_filers = {r[0]: r for r in con.execute("SELECT cik, name, accession, filed, form, aum FROM lv.filers")}
            live_rows = con.execute("SELECT cik, kind, shares, value FROM lv.h WHERE cusip = ?", (cusip,)).fetchall()
            bulk_filed = {r[0] for r in con.execute("SELECT cik FROM filers WHERE q = 0")}
            live = {"filers": live_filers, "rows": live_rows, "bulk_filed": bulk_filed}
    finally:
        con.close()
    out = {}

    def new_row(cik, name, acc, filed, form, aum):
        return {"cik": cik, "name": name, "accession": acc, "filed": filed, "form": form, "aum": aum,
                "shares": 0.0, "stock_value": 0.0, "call_value": 0.0, "put_value": 0.0,
                "call_shares": 0.0, "put_shares": 0.0, "option_positions": 0, "stock_positions": 0, "is_current": False}

    def fill(r, kind, shares, value):
        if kind == "SH":
            r["shares"], r["stock_value"], r["stock_positions"] = shares, value, 1
        else:
            r[kind.lower() + "_value"], r[kind.lower() + "_shares"] = value, shares
            r["option_positions"] += 1
    for cik, name, acc, filed, form, aum, kind, shares, value in cur:
        fill(out.setdefault(cik, new_row(cik, name, acc, filed, form, aum)), kind, shares, value)
    for cik, r in out.items():
        r["prev_shares"], r["prev_stock_value"] = prev.get(cik, (None, None))
        r["filed_prev_quarter"] = cik in prev_filed
        r["hist"] = [(r["prev_shares"], r["prev_stock_value"], r["filed_prev_quarter"]),
                     (r["shares"], r["stock_value"], True), (None, None, False)]
    if live:
        by_live = {}
        for cik, kind, shares, value in live["rows"]:
            by_live.setdefault(cik, []).append((kind, shares, value))
        for cik, f in live["filers"].items():
            old = out.pop(cik, None)
            if cik not in by_live:
                continue                                  # reported the new quarter without this security
            r = new_row(cik, f[1], f[2], f[3], f[4], f[5])
            for kind, shares, value in by_live[cik]:
                fill(r, kind, shares, value)
            r["is_current"] = True
            had = old is not None and old["stock_positions"]
            r["prev_shares"], r["prev_stock_value"] = (old["shares"], old["stock_value"]) if had else (None, None)
            r["filed_prev_quarter"] = cik in live["bulk_filed"]
            r["hist"] = [old["hist"][0] if old else (None, None, False),
                         (old["shares"], old["stock_value"], True) if had else (None, None, cik in live["bulk_filed"]),
                         (r["shares"], r["stock_value"], True)]
            out[cik] = r
    return list(out.values())


def sold_out_count(db_path, cusip, live_db=None):
    """Filers that held the shares in the previous report, filed a newer one, and no longer hold them."""
    con = _connect(db_path)
    try:
        has_live = _attach_live(con, live_db)
        skip = "AND p.cik NOT IN (SELECT cik FROM lv.filers)" if has_live else ""
        n = con.execute(f"""SELECT count(*) FROM h p WHERE p.cusip = ? AND p.q = 1 AND p.kind = 'SH' {skip}
            AND EXISTS (SELECT 1 FROM filers f WHERE f.q = 0 AND f.cik = p.cik)
            AND NOT EXISTS (SELECT 1 FROM h c WHERE c.q = 0 AND c.cik = p.cik AND c.cusip = p.cusip AND c.kind = 'SH')""",
                        (cusip,)).fetchone()[0]
        if has_live:
            n += con.execute("""SELECT count(*) FROM h p WHERE p.cusip = ? AND p.q = 0 AND p.kind = 'SH'
                AND p.cik IN (SELECT cik FROM lv.filers)
                AND NOT EXISTS (SELECT 1 FROM lv.h c WHERE c.cik = p.cik AND c.cusip = p.cusip AND c.kind = 'SH')""",
                             (cusip,)).fetchone()[0]
        return n
    finally:
        con.close()


def cusips_by_issuer(db_path, prefix, limit=30):
    """(cusip, issuer) pairs whose issuer name starts with `prefix`, biggest first. Wildcards are not honoured."""
    p = (prefix or "").strip().upper()
    if not p or any(c in p for c in "%_\\"):
        return []
    con = _connect(db_path)
    try:
        return [(c, i) for c, i in con.execute(
            """SELECT i.cusip, i.issuer FROM iss i LEFT JOIN (SELECT cusip, SUM(value) v FROM h WHERE q = 0 GROUP BY cusip) t
               ON t.cusip = i.cusip WHERE i.issuer LIKE ? ESCAPE '\\' ORDER BY COALESCE(t.v, 0) DESC LIMIT ?""", (p + "%", limit))]
    finally:
        con.close()


def has_holders(db_path, cusip):
    con = _connect(db_path)
    try:
        return con.execute("SELECT 1 FROM h WHERE cusip = ? AND q = 0 LIMIT 1", (cusip,)).fetchone() is not None
    finally:
        con.close()
