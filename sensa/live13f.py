"""Closing the 13F lag: the SEC bulk data set for a quarter appears weeks after the quarter's reports start arriving.

This module reads each new 13F-HR for the *next* quarter straight from EDGAR (daily form index -> cover page ->
information table) and keeps them in a small SQLite file next to the bulk index. Filers that already reported
use their new holdings; everyone else is carried from the bulk data set until their report arrives."""

import os
import re
import sqlite3
import threading
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

from markov.data_providers import DataUnavailable
from sensa.jobs import BackgroundJob

DAILY_INDEX = "https://www.sec.gov/Archives/edgar/daily-index/{y}/QTR{q}/form.{d}.idx"
_LINE = re.compile(r"^(13F-HR(?:/A)?)\s+(.+?)\s+(\d{1,10})\s+(\d{8})\s+edgar/data/\d+/(\d{10}-\d{2}-\d{6})\.txt\s*$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS filers(cik TEXT PRIMARY KEY, name TEXT, accession TEXT, filed TEXT, form TEXT, period TEXT, aum REAL);
CREATE TABLE IF NOT EXISTS h(cik TEXT, cusip TEXT, kind TEXT, shares REAL, value REAL);
CREATE INDEX IF NOT EXISTS live_h_cusip ON h(cusip);
CREATE TABLE IF NOT EXISTS seen(accession TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY);
"""


def next_quarter_end(period):
    y, m = int(period[:4]), int(period[5:7])
    m += 3
    if m > 12:
        y, m = y + 1, m - 12
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return f"{y:04d}-{m:02d}-{last:02d}"


def parse_daily_index(text):
    out = []
    for line in text.splitlines():
        m = _LINE.match(line.rstrip())
        if m:
            d = m.group(4)
            out.append({"form": m.group(1), "name": m.group(2).strip(), "cik": f"{int(m.group(3)):010d}",
                        "filed": f"{d[:4]}-{d[4:6]}-{d[6:]}", "accession": m.group(5)})
    return out


def parse_infotable(xml_text, scale):
    """[(cusip, issuer, kind, shares, value)] for share positions; bond principal is dropped. kind: SH, CALL or PUT."""
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise DataUnavailable("refusing XML with DTD/entities")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise DataUnavailable(f"bad XML: {e}") from e
    rows = []
    for it in root.iter():
        if not it.tag.endswith("infoTable"):
            continue
        g = lambda p: (it.findtext("{*}" + p) or "").strip()
        if (it.findtext("{*}shrsOrPrnAmt/{*}sshPrnamtType") or "").strip().upper() != "SH":
            continue
        try:
            shares = float(it.findtext("{*}shrsOrPrnAmt/{*}sshPrnamt") or 0)
            value = float(g("value")) * scale
        except ValueError:
            continue
        pc = g("putCall").upper()
        rows.append((g("cusip"), g("nameOfIssuer"), pc if pc in ("CALL", "PUT") else "SH", shares, value))
    return rows


class LiveStore:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._lock = threading.Lock()
        with self._con() as con:
            con.executescript(_SCHEMA)

    def _con(self):
        return sqlite3.connect(self.path, timeout=30)

    def seen(self):
        with self._con() as con:
            return {r[0] for r in con.execute("SELECT accession FROM seen")}

    def mark_seen(self, accession):
        with self._lock, self._con() as con:
            con.execute("INSERT OR IGNORE INTO seen VALUES(?)", (accession,))

    def days_done(self):
        with self._con() as con:
            return {r[0] for r in con.execute("SELECT day FROM days")}

    def mark_day(self, day):
        with self._lock, self._con() as con:
            con.execute("INSERT OR IGNORE INTO days VALUES(?)", (day,))

    def add(self, filer, rows):
        """Store one filer's report (replacing an older one) as one transaction."""
        with self._lock, self._con() as con:
            con.execute("DELETE FROM h WHERE cik = ?", (filer["cik"],))
            con.execute("INSERT OR REPLACE INTO filers VALUES(?,?,?,?,?,?,?)", (
                filer["cik"], filer["name"], filer["accession"], filer["filed"], filer["form"], filer["period"], filer["aum"]))
            agg = {}
            for cusip, _issuer, kind, shares, value in rows:
                a = agg.setdefault((cusip, kind), [0.0, 0.0])
                a[0] += shares
                a[1] += value
            con.executemany("INSERT INTO h VALUES(?,?,?,?,?)", [(filer["cik"], c, k, s, v) for (c, k), (s, v) in agg.items()])
            con.execute("INSERT OR IGNORE INTO seen VALUES(?)", (filer["accession"],))

    def filers(self):
        with self._con() as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute("SELECT * FROM filers ORDER BY cik")]

    def holdings(self, cik):
        with self._con() as con:
            return con.execute("SELECT cusip, kind, shares, value FROM h WHERE cik = ? ORDER BY cusip, kind", (cik,)).fetchall()

    def purge_through(self, period):
        """Forget live reports for quarters the bulk data set now covers."""
        with self._lock, self._con() as con:
            con.execute("DELETE FROM h WHERE cik IN (SELECT cik FROM filers WHERE period <= ?)", (period,))
            con.execute("DELETE FROM filers WHERE period <= ?", (period,))


class LiveUpdater(BackgroundJob):
    def __init__(self, store, tf, bulk_period, today=date.today, sleep=None, min_interval=0.3):
        super().__init__("reading new 13F reports from EDGAR")
        import time
        self.store, self.tf, self.bulk_period = store, tf, bulk_period
        self.today, self._sleep, self.min_interval = today, sleep or time.sleep, min_interval

    def check(self, force=False):
        bulk = self.bulk_period()
        self.store.purge_through(bulk)
        target = next_quarter_end(bulk)
        start = datetime.strptime(target, "%Y-%m-%d").date() + timedelta(days=1)
        today = self.today()
        if today < start:
            return None
        done, seen = self.store.days_done(), self.store.seen()
        todo, day = [], start
        while day <= today:
            if day.weekday() < 5 and (day.isoformat() not in done or day == today):
                todo.append(day)
            day += timedelta(days=1)
        filings = []
        for d in todo:
            try:
                text = self.tf.fetch(DAILY_INDEX.format(y=d.year, q=(d.month - 1) // 3 + 1, d=d.strftime("%Y%m%d")))
            except DataUnavailable:
                continue                              # a holiday has no file; retried next run (one cheap request)
            filings.extend(f for f in parse_daily_index(text) if f["form"] == "13F-HR" and f["accession"] not in seen)
            if d != today:
                self.store.mark_day(d.isoformat())
        added = 0
        for f in filings:
            try:
                cov = self.tf.cover(f["cik"], f["accession"], f["filed"])
                if cov["period"] != target:
                    self.store.mark_seen(f["accession"])
                    continue
                rows = self.tf.infotable(f["cik"], f["accession"], f["filed"])
            except DataUnavailable:
                continue                              # retried on the next run
            self.store.add({**f, "period": cov["period"], "aum": cov["value"]}, rows)
            added += 1
            self._sleep(self.min_interval)
        return added or None
