"""Orchestrates the signal research: historical 13F overviews (one per quarter pair, cached), historical insider trades,
prices, then the point-in-time evidence. All I/O is injected so the flow can be tested without SEC downloads."""

import json
import os
import time
from datetime import date, timedelta

from markov.data_providers import DataUnavailable
from sensa.signal_history import build_samples, summarize_evidence


def signal_date_of(overview):
    """The day the 13F picture of a quarter was mostly public: when 80% of the top funds had filed."""
    filed = sorted(f["filed"] for f in overview.get("funds", []) if f.get("filed"))
    if filed:
        return filed[int(0.8 * (len(filed) - 1))]
    return (date.fromisoformat(overview["period"]) + timedelta(days=45)).isoformat()


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def hist_overviews(data_dir, sets, ensure_zip, build, notes=None, signal_dates=None):
    """sets: 13F data-set windows, newest first. One overview per consecutive pair (this quarter vs the one before)."""
    out = []
    for i in range(len(sets) - 1):
        cur, prev = sets[i], sets[i + 1]
        path = os.path.join(data_dir, "hist", f"overview_{cur['period']}.json")
        ov = _read(path)
        if ov is None:
            try:
                ov = build(ensure_zip(cur), ensure_zip(prev), cur["period"], prev["period"])
            except DataUnavailable as e:
                if notes is not None:
                    notes.append(f"{cur['period']} skipped: {e}")
                continue
            _write(path, ov)
        ov["signal_date"] = (signal_dates or {}).get(cur["period"]) or signal_date_of(ov)
        out.append(ov)
    return sorted(out, key=lambda o: o["period"])


def hist_insiders(data_dir, isets, ensure_zip, load, notes=None, newest_ttl=86400):
    trades = []
    for i, s in enumerate(isets):
        path = os.path.join(data_dir, "hist", f"insiders_{s['quarter']}.json")
        fresh = os.path.exists(path) and (i > 0 or time.time() - os.path.getmtime(path) < newest_ttl)      # the newest quarter keeps growing
        t = _read(path) if fresh else None
        if t is None:
            try:
                t = load(ensure_zip(s))
            except DataUnavailable as e:
                if notes is not None:
                    notes.append(f"insiders {s['quarter']} skipped: {e}")
                continue
            _write(path, t)
        trades.extend(t)
    return trades


def research_board(data_dir, sets13f, isets, ensure_zip, build_ov, load_ins, closes_fn, defaults, signal_dates=None):
    notes = []
    ovs = hist_overviews(data_dir, sets13f, ensure_zip, build_ov, notes, signal_dates)
    if len(ovs) < 2:
        raise DataUnavailable("need at least two historical quarters to test signals; " + "; ".join(notes))
    trades = hist_insiders(data_dir, isets, ensure_zip, load_ins, notes)
    samples = build_samples(ovs, trades, closes_fn)
    ev = summarize_evidence(samples, defaults=defaults)
    tickers = {s["ticker"] for o in ovs for s in o["stocks"] if s["kind"] in ("stock", "adr") and s.get("ticker")}
    ev["meta"] = {"quarters": len(ovs), "tickers": len(tickers), "first_signal": ovs[0]["signal_date"], "last_signal": ovs[-1]["signal_date"],
                  "insider_trades": len(trades), "notes": notes}
    return ev
