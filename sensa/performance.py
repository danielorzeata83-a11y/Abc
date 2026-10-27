"""What holders, politicians and insiders would have earned: pure maths over holdings/trades and a price book.

Everything is buy-and-hold on reported positions; reports arrive late, so each result is given both from the
trade / quarter-end date and from the day the report became public (the part you could actually have copied)."""


def _pct(now, then):
    return round((now / then - 1) * 100, 2) if now is not None and then else None


def _spy(prices, day, now=None):
    p = prices.on_or_after("SPY", day)
    last = prices.last("SPY")
    return _pct(last[1], p[1]) if p and last else None


def fund_performance(positions, ticker_of, prices, period, filed, top_n=60, rows_n=25):
    """positions: [{cusip, issuer, shares, value}] reported at `period`; filed: the report's public date."""
    total = sum(p["value"] for p in positions) or 0.0
    priced = []
    for p in sorted(positions, key=lambda p: p["value"], reverse=True)[:top_n]:
        t = ticker_of(p["cusip"])
        if not t:
            continue
        end, fil, now = prices.on_or_before(t, period), prices.on_or_after(t, filed), prices.last(t)
        if end and fil and now:
            priced.append({**p, "ticker": t, "px_end": end[1], "px_filed": fil[1], "px_now": now[1], "now_date": now[0]})
    sh = lambda key: sum(p["shares"] * p[key] for p in priced)
    value_end, value_filed, value_now = sh("px_end"), sh("px_filed"), sh("px_now")
    spy_end, spy_fil, spy_now = prices.on_or_before("SPY", period), prices.on_or_after("SPY", filed), prices.last("SPY")
    rows = [{"ticker": p["ticker"], "issuer": p["issuer"], "shares": p["shares"],
             "weight": round(p["value"] / total * 100, 2) if total else None, "px_end": p["px_end"], "px_filed": p["px_filed"],
             "px_now": p["px_now"], "change_since_filing_pct": _pct(p["px_now"], p["px_filed"]),
             "pnl_since_filing": round(p["shares"] * (p["px_now"] - p["px_filed"]), 2)} for p in priced[:rows_n]]
    return {"period": period, "filed": filed, "as_of": max((p["now_date"] for p in priced), default=None),
            "positions_total": len(positions), "covered_positions": len(priced),
            "covered_pct": round(sum(p["value"] for p in priced) / total * 100, 2) if total else 0.0,
            "value_period_end": round(value_end, 2), "value_now": round(value_now, 2),
            "return_since_period_pct": _pct(value_now, value_end), "return_since_filing_pct": _pct(value_now, value_filed),
            "spy_since_period_pct": _pct(spy_now[1], spy_end[1]) if spy_now and spy_end else None,
            "spy_since_filing_pct": _pct(spy_now[1], spy_fil[1]) if spy_now and spy_fil else None, "rows": rows}


def member_leaderboard(trades, prices, min_buys=3):
    """Per House member: value-weighted return of disclosed purchases since the trade day and since the filing day."""
    by = {}
    for t in trades:
        if not t.get("ticker") or t.get("suspect"):
            continue
        m = by.setdefault(t["member"], {"buys": [], "sells": 0, "volume": 0.0})
        m["volume"] += t["value"]
        if t["type"] in ("sale", "partial sale"):
            m["sells"] += 1
        elif t["type"] == "purchase":
            tr, fi, now = prices.on_or_after(t["ticker"], t["date"]), prices.on_or_after(t["ticker"], t["filed"]), prices.last(t["ticker"])
            if tr and now:
                m["buys"].append({"w": t["value"], "ticker": t["ticker"], "trade": _pct(now[1], tr[1]),
                                  "filing": _pct(now[1], fi[1]) if fi else None,
                                  "spy_trade": _spy(prices, t["date"]), "spy_filing": _spy(prices, t["filed"])})
    out = []
    for member, m in by.items():
        buys = m["buys"]
        if not buys or len(buys) < min_buys:
            continue

        def wavg(key):
            xs = [(b["w"], b[key]) for b in buys if b[key] is not None]
            w = sum(x[0] for x in xs)
            return round(sum(a * b for a, b in xs) / w, 2) if w else None
        rt, rf, st, sf = wavg("trade"), wavg("filing"), wavg("spy_trade"), wavg("spy_filing")
        best = max(buys, key=lambda b: b["trade"])
        out.append({"member": member, "buys": len(buys), "sells": m["sells"], "est_volume": m["volume"],
                    "return_since_trade_pct": rt, "spy_since_trade_pct": st,
                    "alpha_since_trade_pct": round(rt - st, 2) if rt is not None and st is not None else None,
                    "return_since_filing_pct": rf, "spy_since_filing_pct": sf,
                    "alpha_since_filing_pct": round(rf - sf, 2) if rf is not None and sf is not None else None,
                    "best_trade": {"ticker": best["ticker"], "return_pct": best["trade"]}})
    return sorted(out, key=lambda r: (r["return_since_filing_pct"] is None, -(r["return_since_filing_pct"] or 0)))


def insider_holdings(trades, prices):
    """Latest reported balance per (insider, company), valued at the last close, with the insider's own buy return."""
    by = {}
    for t in trades:
        by.setdefault((t["owner"], t["symbol"]), []).append(t)
    out = []
    for (owner, sym), ts in by.items():
        with_balance = [t for t in ts if t.get("owned_after")]
        if not with_balance:
            continue
        last = max(with_balance, key=lambda t: t["date"])
        now = prices.last(sym)
        buys = [t for t in ts if t["side"] == "buy"]
        bs = sum(t["shares"] for t in buys)
        avg = sum(t["value"] for t in buys) / bs if bs else None
        out.append({"owner": owner, "symbol": sym, "issuer": last.get("issuer", ""), "role": last.get("role", ""),
                    "shares": last["owned_after"], "as_of_trade": last["date"],
                    "price": now[1] if now else None, "value": round(last["owned_after"] * now[1], 2) if now else None,
                    "avg_buy_price": round(avg, 4) if avg else None,
                    "buy_return_pct": _pct(now[1], avg) if now and avg else None})
    return sorted(out, key=lambda r: -(r["value"] or 0))


def insider_buy_performance(trades, prices, top=5):
    """How open-market insider purchases have done since the purchase price, against SPY over the same days."""
    rows = []
    for t in trades:
        if t["side"] != "buy":
            continue
        now, entry = prices.last(t["symbol"]), prices.on_or_after(t["symbol"], t["date"])
        r = _pct(now[1], entry[1]) if now and entry else None      # same adjusted series both ends: splits cancel out
        if r is None:
            continue
        rows.append({"symbol": t["symbol"], "owner": t["owner"], "role": t.get("role", ""), "date": t["date"],
                     "price": t["price"], "return_pct": r, "spy_pct": _spy(prices, t["date"])})
    if not rows:
        return {"n": 0, "avg_return_pct": None, "median_return_pct": None, "spy_pct": None, "win_rate_pct": None, "best": [], "worst": []}
    spy = [r["spy_pct"] for r in rows if r["spy_pct"] is not None]
    ordered = sorted(rows, key=lambda r: r["return_pct"], reverse=True)
    mid = sorted(r["return_pct"] for r in rows)
    median = mid[len(mid) // 2] if len(mid) % 2 else round((mid[len(mid) // 2 - 1] + mid[len(mid) // 2]) / 2, 2)
    return {"n": len(rows), "avg_return_pct": round(sum(r["return_pct"] for r in rows) / len(rows), 2), "median_return_pct": median,
            "spy_pct": round(sum(spy) / len(spy), 2) if spy else None,
            "win_rate_pct": round(sum(1 for r in rows if r["return_pct"] > 0) / len(rows) * 100, 1),
            "best": ordered[:top], "worst": ordered[::-1][:top]}
