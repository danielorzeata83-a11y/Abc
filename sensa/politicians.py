"""Stock trades by members of the US House from their Periodic Transaction Reports (STOCK Act).

The Clerk of the House publishes a filing index and one PDF per report. This module reads both.
Senate reports are not covered: the Senate site requires accepting terms in a browser session."""

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from markov.data_providers import DataUnavailable

_HONORIFIC = re.compile(r"^(?:Hon\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+", re.I)
_DATE = r"\d{1,2}/\d{1,2}/\d{4}"
# the type letter + two dates + amount; the asset text may sit before it on the same line
_TX = re.compile(rf"^(?P<pre>.*?)(?<![A-Za-z0-9])(?P<t>[PSE])(?:\s*\(partial\))?\s+(?P<d1>{_DATE})\s+(?P<d2>{_DATE})\s+"
                 r"(?P<amt>(?:Spouse/DC\s+)?Over(?:\s+\$[\d,]+(?:\.\d+)?)?|\$[\d,]+(?:\.\d+)?(?:\s*-\s*(?:\$[\d,]+(?:\.\d+)?)?)?)(?:\s+[YN])?\s*$")
_PARTIAL = re.compile(r"(?<![A-Za-z0-9])S\s*\(partial\)\s+" + _DATE)
_TRAILER = re.compile(r"^(F\s+S\s*:|S\s+O\s*:|D\s*:|C\s*:|L\s*:)")
_OWNER = re.compile(r"^(SP|JT|DC)\s+(.*)$")
_TICKER = re.compile(r"\(([A-Z][A-Z0-9.\-]{0,5})\)\s*(?:\[[A-Z]{2}\])?\s*$")
_ASSET_TYPE = re.compile(r"\[([A-Z]{2})\]\s*$")
_MONEY = re.compile(r"\$([\d,]+(?:\.\d+)?)")
_KIND = {"P": "purchase", "S": "sale", "E": "exchange"}


def _iso(d):
    m, dd, y = d.split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(dd):02d}"


def _amount(text):
    nums = [float(x.replace(",", "")) for x in _MONEY.findall(text)]
    nums = [int(n) if n == int(n) else n for n in nums]
    if "over" in text.lower() or len(nums) == 1:
        return nums[0], None
    return nums[0], nums[1]


def _clean_asset(parts):
    """Asset name from the lines before a transaction. A name over 120 characters is a wrapped description
    plus the name: keep the shortest tail of lines that already holds real letters (not just [ST] / (TICKER))."""
    asset = " ".join(parts).strip()
    if len(asset) <= 120:
        return asset
    for keep in (1, 2, 3):
        tail = " ".join(parts[-keep:]).strip()
        letters = re.sub(r"\[[A-Z]{2}\]|\([A-Z][A-Z0-9.\-]{0,5}\)", "", tail)
        if len(re.sub(r"[^A-Za-z]", "", letters)) >= 8:
            return tail
    return " ".join(parts[-3:]).strip()


def parse_ptr(text):
    """One report -> {"member", "state", "district", "trades": [...]}."""
    if not text or not text.strip():
        raise DataUnavailable("report has no text layer (scanned image?)")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)       # some PDFs encode spaces as NUL characters
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.splitlines()]
    name = state = district = None
    start = 0
    for i, l in enumerate(lines):
        m = re.match(r"Name:\s*(.+)$", l)
        if m and name is None:
            name = re.sub(r"\s+", " ", _HONORIFIC.sub("", m.group(1).strip()))
        m = re.match(r"State/District:\s*([A-Z]{2})(\d{2}|AL)?", l)
        if m and state is None:
            state, district = m.group(1), m.group(2) or ""
        if "$200?" in l and not start:
            start = i + 1
    trades, buf, i = [], [], start
    while i < len(lines):
        l = lines[i]
        i += 1
        if not l:
            continue
        if l.startswith("* For the complete list"):
            break
        if "$200?" in l:                       # the table header repeats on every page: drop what it dragged in
            buf = []
            continue
        if _TRAILER.match(l):
            if trades and re.match(r"^S\s+O\s*:", l):
                trades[-1]["account"] = re.sub(r"^S\s+O\s*:\s*", "", l).strip()
            continue
        probe = l
        if re.search(r"(?:-|Over)\s*$", l) and i < len(lines) and re.match(r"^\$[\d,]+(?:\.\d+)?(?:\s+[YN])?$", lines[i]):
            probe = l + " " + lines[i]                      # the upper bound wrapped onto the next line
            skip = 1
        else:
            skip = 0
        m = _TX.match(probe)
        if not m:
            buf.append(l)
            continue
        i += skip
        kind = "partial sale" if _PARTIAL.search(probe) else _KIND[m.group("t")]
        pre = m.group("pre").strip()
        parts = buf + ([pre] if pre else [])
        asset = _clean_asset(parts)
        buf = []
        owner = ""
        om = _OWNER.match(asset)
        if om:
            owner, asset = om.group(1), om.group(2).strip()
        atype = _ASSET_TYPE.search(asset)
        asset = _ASSET_TYPE.sub("", asset).strip()
        tk = _TICKER.search(asset + " ")
        ticker = tk.group(1) if tk else None
        if tk:
            asset = asset[:tk.start()].strip()
        low, high = _amount(m.group("amt"))
        trades.append({"asset": re.sub(r"\s+", " ", asset), "ticker": ticker, "asset_type": atype.group(1) if atype else "",
                       "owner": owner, "type": kind, "date": _iso(m.group("d1")), "notified": _iso(m.group("d2")),
                       "amount_low": low, "amount_high": high,
                       "value": (low + high) / 2 if high else float(low), "account": ""})
    if not trades:
        raise DataUnavailable("no transactions found in the report")
    return {"member": name or "", "state": state or "", "district": district or "", "trades": trades}


def parse_index(xml_text):
    """The Clerk's yearly filing index -> Periodic Transaction Reports (type P), newest first."""
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise DataUnavailable("refusing XML with DTD/entities")
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError as e:
        raise DataUnavailable(f"bad filing index: {e}") from e
    out = []
    for m in root.iter("Member"):
        if (m.findtext("FilingType") or "").strip() != "P":
            continue
        try:
            filed = _iso((m.findtext("FilingDate") or "").strip())
        except ValueError:
            continue
        name = " ".join(x for x in ((m.findtext("First") or "").strip(), (m.findtext("Last") or "").strip(),
                                    (m.findtext("Suffix") or "").strip()) if x)
        out.append({"doc_id": (m.findtext("DocID") or "").strip(), "filed": filed, "name": name,
                    "state_dst": (m.findtext("StateDst") or "").strip()})
    return sorted((d for d in out if d["doc_id"].isdigit()), key=lambda d: (d["filed"], d["doc_id"]), reverse=True)


def extract_text(path):
    """Text of a PDF, in reading order: pypdf (pure Python), else poppler's pdftotext -raw."""
    text = ""
    try:
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception:                      # missing library or an unreadable PDF: try the other extractor
        text = ""
    if text.strip():
        return text
    exe = shutil.which("pdftotext")
    if exe:
        try:
            out = subprocess.run([exe, "-raw", path, "-"], capture_output=True, timeout=60)
            text = out.stdout.decode("utf-8", "replace")
        except (OSError, subprocess.SubprocessError):
            text = ""
    if not text.strip():
        raise DataUnavailable("no text could be read from the PDF (install `pip install pypdf`, or poppler)")
    return text


# ------------------------------------------------------------------ build / store / serve
import json
import os
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from sensa.jobs import BackgroundJob

_INDEX_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
_PDF_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc}.pdf"
_DOC = re.compile(r"^[0-9]{1,12}$")


class PoliticiansService(BackgroundJob):
    def __init__(self, data_dir, download, extract=extract_text, today=date.today, workers=6, retry_days=1):
        super().__init__("downloading House disclosure reports")
        self.data_dir, self.download, self.extract = data_dir, download, extract
        self.today, self.workers, self.retry_days = today, workers, retry_days
        self._data = None

    # ---- files
    def _agg_path(self):
        return os.path.join(self.data_dir, "politicians.json")

    def _doc_path(self, doc):
        if not _DOC.match(doc):
            raise ValueError("bad document id")
        return os.path.join(self.data_dir, "ptr", f"{doc}.json")

    @staticmethod
    def _write(path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        os.replace(tmp, path)

    def _years(self):
        t = self.today()
        return [t.year] + ([t.year - 1] if t.month <= 3 else [])      # reports are filed up to 45 days after a trade

    def _cached(self, doc):
        try:
            with open(self._doc_path(doc), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _due(self, rec):
        """Needs (re)processing: never seen, or failed long enough ago to try again."""
        if rec is None:
            return True
        if "error" not in rec:
            return False
        try:
            return date.fromisoformat(rec["tried"]) + timedelta(days=self.retry_days) <= self.today()
        except (KeyError, ValueError):
            return True

    # ---- build
    def _process(self, year, d):
        fd, tmp = tempfile.mkstemp(suffix=".pdf", dir=self.data_dir)
        os.close(fd)
        try:
            self.download(_PDF_URL.format(year=year, doc=d["doc_id"]), tmp)
            parsed = parse_ptr(self.extract(tmp))
            rec = {"doc_id": d["doc_id"], "year": year, "filed": d["filed"], "name": d["name"], "state_dst": d["state_dst"],
                   "member": parsed["member"] or d["name"], "trades": parsed["trades"]}
        except DataUnavailable as e:
            rec = {"doc_id": d["doc_id"], "year": year, "filed": d["filed"], "name": d["name"], "state_dst": d["state_dst"],
                   "error": str(e), "tried": self.today().isoformat()}
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        self._write(self._doc_path(d["doc_id"]), rec)
        return rec

    def check(self, force=False):
        os.makedirs(self.data_dir, exist_ok=True)
        todo = []
        for year in self._years():
            zpath = os.path.join(self.data_dir, f"index-{year}.zip")
            try:
                self.download(_INDEX_URL.format(year=year), zpath + ".part")
                os.replace(zpath + ".part", zpath)
                with zipfile.ZipFile(zpath) as z:
                    docs = parse_index(z.read(f"{year}FD.xml").decode("utf-8", "replace"))
            except (zipfile.BadZipFile, KeyError, OSError) as e:
                raise DataUnavailable(f"cannot read the House filing index for {year} ({type(e).__name__})") from None
            todo += [(year, d) for d in docs if force or self._due(self._cached(d["doc_id"]))]
        if not todo and os.path.exists(self._agg_path()):
            return None
        with ThreadPoolExecutor(max_workers=max(1, min(self.workers, len(todo) or 1))) as pool:
            recs = list(pool.map(lambda yd: self._process(*yd), todo))
        failed = sum(1 for r in recs if "error" in r)
        agg = self._aggregate()
        self._write(self._agg_path(), agg)
        self._data = None
        return {"new": len(recs) - failed, "failed": failed, "trades": len(agg["trades"])}

    def _aggregate(self):
        ok, bad, trades, as_of = 0, 0, [], ""
        ptr_dir = os.path.join(self.data_dir, "ptr")
        for name in sorted(os.listdir(ptr_dir)) if os.path.isdir(ptr_dir) else []:
            rec = self._cached(name[:-5]) if name.endswith(".json") else None
            if rec is None:
                continue
            if "error" in rec:
                bad += 1
                continue
            ok += 1
            as_of = max(as_of, rec["filed"])
            for t in rec["trades"]:
                trades.append({**t, "member": rec["member"], "state_dst": rec["state_dst"], "doc_id": rec["doc_id"],
                               "filed": rec["filed"], "suspect": t["date"] > rec["filed"]})   # typos: traded after reporting
        return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "as_of": as_of,
                "reports": ok, "failed": bad, "trades": trades}

    # ---- serve
    def _load(self):
        if self._data is None:
            try:
                with open(self._agg_path(), encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (OSError, ValueError):
                raise DataUnavailable("No congressional trade data yet. Press Update to read the House disclosure reports.") from None
        return self._data

    def trades_since(self, days):
        """Trades dated in the last `days` before the newest report (suspect dates left out)."""
        d = self._load()
        if days <= 0 or not d["as_of"]:
            return []
        start = (date.fromisoformat(d["as_of"]) - timedelta(days=days)).isoformat()
        return [t for t in d["trades"] if t["date"] >= start and not t.get("suspect")]

    def overview(self, days=90, side=None, ticker=None, member=None, limit=100):
        d = self._load()
        start = (date.fromisoformat(d["as_of"]) - timedelta(days=days)).isoformat() if d["as_of"] else ""
        in_window = [t for t in d["trades"] if t["date"] >= start]
        suspect = sum(1 for t in in_window if t.get("suspect"))
        win = [t for t in in_window if not t.get("suspect")]
        if ticker:
            win = [t for t in win if t["ticker"] == ticker.upper()]
        if member:
            win = [t for t in win if member.lower() in t["member"].lower()]
        if side:
            win = [t for t in win if (t["type"] in ("sale", "partial sale")) == (side == "sell") and t["type"] != "exchange"]
        buys = [t for t in win if t["type"] == "purchase" and t["ticker"]]
        sells = [t for t in win if t["type"] in ("sale", "partial sale") and t["ticker"]]

        def rank(rows):
            g = {}
            for t in rows:
                x = g.setdefault(t["ticker"], {"ticker": t["ticker"], "asset": t["asset"], "members": set(), "trades": 0, "value": 0.0})
                x["members"].add(t["member"])
                x["trades"] += 1
                x["value"] += t["value"]
            out = [{**x, "members": len(x["members"])} for x in g.values()]
            return sorted(out, key=lambda x: (x["members"], x["value"]), reverse=True)[:15]
        by_member = {}
        for t in win:
            m = by_member.setdefault(t["member"], {"member": t["member"], "state_dst": t["state_dst"], "trades": 0, "value": 0.0})
            m["trades"] += 1
            m["value"] += t["value"]
        latest = sorted(win, key=lambda t: (t["date"], t["filed"]), reverse=True)[:limit]
        return {"as_of": d["as_of"], "generated": d["generated"], "days": days, "reports": len({t["doc_id"] for t in win}),
                "trades": len(win), "suspect": suspect, "latest": latest, "top_bought": rank(buys), "top_sold": rank(sells),
                "members": sorted(by_member.values(), key=lambda m: (-m["trades"], m["member"]))[:15]}

    def status(self):
        st = self.state()
        try:
            d = self._load()
            st.update(built_at=d["generated"], as_of=d["as_of"], reports=d["reports"], failed=d["failed"])
        except DataUnavailable:
            st.update(built_at=None, as_of=None, reports=0, failed=0)
        return st
