"""Performance views served to the pages: a fund's portfolio at today's prices, and cached leaderboards.

Leaderboards (funds, House members, insiders) take minutes the first time (prices for hundreds of tickers), so
each one is a background job that writes its result to disk and keeps the last good one if a run fails."""

import json
import os
import threading
import time
from datetime import datetime, timezone

from markov.data_providers import DataUnavailable
from sensa.holders import portfolio_for_cik
from sensa.jobs import BackgroundJob
from sensa.performance import fund_performance


class PerfJob(BackgroundJob):
    def __init__(self, label, compute, path):
        super().__init__(label)
        self.compute, self.path = compute, path

    def check(self, force=False):
        data = self.compute()
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "data": data}, fh)
        os.replace(tmp, self.path)
        return data

    def result(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            raise DataUnavailable("Performance numbers are not computed yet. They are built in the background after "
                                  "start-up (a few minutes the first time); press Compute now to start immediately.") from None

    def status(self):
        st = self.state()
        try:
            st["generated"] = self.result()["generated"]
        except DataUnavailable:
            st["generated"] = None
        return st


class PortfolioService:
    def __init__(self, holders_db, live_db, figi, prices, top_n=40, ttl=3600, clock=time.time):
        self.db, self.live_db, self.figi, self.prices = holders_db, live_db, figi, prices
        self.top_n, self.ttl, self._clock = top_n, ttl, clock
        self._cache, self._lock = {}, threading.Lock()

    def fund(self, cik, top_n=None):
        n = top_n or self.top_n
        key = (cik, n)
        with self._lock:
            hit = self._cache.get(key)
            if hit and self._clock() - hit[0] < self.ttl:
                return hit[1]
        p = portfolio_for_cik(self.db, cik, self.live_db)
        if p is None:
            raise KeyError(cik)
        top = sorted(p["positions"], key=lambda x: x["value"], reverse=True)[:n]
        info = self.figi.info([x["cusip"] for x in top])
        tickers = {c: v["ticker"] for c, v in info.items() if v.get("kind") in ("stock", "adr", "etf") and v.get("ticker")}
        self.prices.warm(list(tickers.values()) + ["SPY"])
        r = fund_performance(p["positions"], tickers.get, self.prices, p["period"], p["filed"], top_n=n)
        r.update(cik=cik, name=p["name"])
        with self._lock:
            self._cache[key] = (self._clock(), r)
        return r


def funds_board(overview, portfolio, top_n=25):
    """The top funds ranked by what their reported portfolio has returned since the report became public."""
    rows = []
    for f in overview["funds"]:
        try:
            r = portfolio.fund(f["cik"], top_n=top_n)
        except (KeyError, DataUnavailable):
            continue
        rows.append({"rank": f["rank"], "cik": f["cik"], "name": f["name"], "aum": f["aum"], "period": r["period"], "filed": r["filed"],
                     "return_since_period_pct": r["return_since_period_pct"], "return_since_filing_pct": r["return_since_filing_pct"],
                     "spy_since_period_pct": r["spy_since_period_pct"], "spy_since_filing_pct": r["spy_since_filing_pct"],
                     "covered_pct": r["covered_pct"]})
    return sorted(rows, key=lambda r: (r["return_since_filing_pct"] is None, -(r["return_since_filing_pct"] or 0)))


def members_board(politicians, prices, days=365):
    from sensa.performance import member_leaderboard
    trades = politicians.trades_since(days)
    prices.warm(sorted({t["ticker"] for t in trades if t.get("ticker") and t["type"] == "purchase"} | {"SPY"}))
    return member_leaderboard(trades, prices)


def insiders_board(insiders, prices, days=180, min_buy=25_000, min_balance_trade=100_000):
    from sensa.performance import insider_buy_performance, insider_holdings
    trades = insiders.trades_since(days)
    buys = [t for t in trades if t["side"] == "buy" and t["value"] >= min_buy]
    big = [t for t in trades if t["value"] >= min_balance_trade and t.get("owned_after")]
    prices.warm(sorted({t["symbol"] for t in buys} | {t["symbol"] for t in big} | {"SPY"}))
    return {"performance": insider_buy_performance(buys, prices), "holdings": insider_holdings(big, prices)[:50]}


def picks_board(overview_fn, prices, insiders, politicians, adjusted_get, years=5, backtest_n=40, track=None, fundamentals=None, research_fn=None, min_evidence_dates=6):
    """Today's top stocks and ETFs plus an out-of-sample test of the price part of the rule (the picks are kept if the test fails)."""
    import pandas as pd
    from sensa.lab_data import load_prices
    from sensa.picks import build_picks
    from sensa.picks_backtest import rank_backtest

    def trades(src):
        if src is None:
            return []
        try:
            return src.trades_since(90)
        except DataUnavailable:
            return []
    overview = overview_fn()
    evidence = None
    if research_fn is not None:
        try:
            evidence = research_fn()
        except DataUnavailable:
            evidence = None
    weights = evidence["weights"]["evidence"] if evidence and evidence["n_signal_dates"] >= min_evidence_dates else None
    out = build_picks(overview, prices, trades(insiders), trades(politicians), fundamentals=fundamentals, stock_weights=weights)
    out["method"]["weights_source"] = "evidence" if weights else "default"
    out["evidence"] = evidence
    if track is not None:
        track.record(out)
        out["track_record"] = track.summary(prices)
    try:
        from sensa.regime_filter import current_regime, gate_backtest
        spy = adjusted_get("SPY", 20)
        d, c = [x[0] for x in spy], [x[1] for x in spy]
        reg = current_regime(c, d)
        if reg:
            reg["backtest"] = gate_backtest(c, d)
        out["regime"] = reg
    except (DataUnavailable, ValueError):
        out["regime"] = None
    held = sorted((s for s in overview["stocks"] if s["kind"] in ("stock", "adr") and not s.get("gone") and not s.get("new_listing")),
                  key=lambda s: (s["holders"], s["value"]), reverse=True)[:backtest_n]
    try:
        P, manifest = load_prices([s["ticker"] for s in held], lambda t: adjusted_get(t, years), min_rows=700)
        bench = None
        try:
            bench = pd.Series(dict(adjusted_get("SPY", years)))
        except DataUnavailable:
            pass
        out["backtest"] = rank_backtest(P, benchmark=bench)
        out["backtest"]["dropped"] = manifest["dropped"]
        out["backtest_error"] = None
    except (DataUnavailable, ValueError) as e:
        out["backtest"], out["backtest_error"] = None, str(e)[:300]
    return out


def brief_board(picks_fn, track, insiders, politicians, watcher, service, notifier=None, extra_fn=None, days=14):
    """Builds today's brief from the latest picks and the previous day's snapshot, stores it and pushes new alerts once."""
    from sensa.brief import build_brief
    picks = picks_fn()
    snaps = [s for s in track.snapshots() if s["date"] < picks["as_of"]]

    def trades(src):
        if src is None:
            return []
        try:
            return src.trades_since(days)
        except DataUnavailable:
            return []
    try:
        events = watcher.events() if watcher is not None else []
    except DataUnavailable:
        events = []
    extra = extra_fn() if extra_fn else []
    brief = service.store(build_brief(picks, snaps[-1] if snaps else None, trades(insiders), trades(politicians), events, extra=extra))
    if notifier is not None:
        service.notify(brief, notifier)
    return brief
