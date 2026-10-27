"""Pure dashboard calculations (no network): movers, analyst consensus,
call/put ratio, yield curve. Providers feed these; tests need no network."""


def _change_pct(q):
    """Prefer the provider's own day change; fall back to price vs prev_close."""
    if q.get("change_pct") is not None:
        return round(q["change_pct"], 2)
    price, prev = q.get("price"), q.get("prev_close")
    if not price or not prev or prev <= 0:
        return None
    return round((price - prev) / prev * 100, 2)


def movers(quotes, n=10):
    """quotes: {sym: {"price", "prev_close"}} -> top-n gainers / losers by % change."""
    rows = []
    for sym, q in quotes.items():
        chg = _change_pct(q)
        if chg is None or not q.get("price"):
            continue
        rows.append({"symbol": sym, "price": q["price"], "change_pct": chg})
    rows.sort(key=lambda r: r["change_pct"], reverse=True)
    losers = sorted(rows, key=lambda r: r["change_pct"])[:n]
    return {"gainers": [r for r in rows[:n] if r["change_pct"] > 0],
            "losers": [r for r in losers if r["change_pct"] < 0]}


def analyst_consensus(trends):
    """Finnhub recommendation-trends (list of periods) -> latest buy/hold/sell."""
    if not trends:
        return None
    t = max(trends, key=lambda r: r["period"])
    buy = t.get("strongBuy", 0) + t.get("buy", 0)
    sell = t.get("sell", 0) + t.get("strongSell", 0)
    hold = t.get("hold", 0)
    verdict = "Buy" if buy > max(hold, sell) else "Sell" if sell > max(hold, buy) else "Hold"
    return {"period": t["period"], "buy": buy, "hold": hold, "sell": sell,
            "verdict": verdict}


def cp_ratio(chain):
    """Tradier chain rows -> call/put volume and open-interest ratios."""
    tot = {"call": [0, 0], "put": [0, 0]}
    for o in chain:
        side = tot.get(o.get("option_type"))
        if side is not None:
            side[0] += o.get("volume") or 0
            side[1] += o.get("open_interest") or 0

    def ratio(c, p):
        return round(c / p, 2) if p else None

    return {"call_volume": tot["call"][0], "put_volume": tot["put"][0],
            "volume_ratio": ratio(tot["call"][0], tot["put"][0]),
            "oi_ratio": ratio(tot["call"][1], tot["put"][1])}


def gex(chain, spot):
    """Dollar gamma exposure per 1% spot move; calls +, puts - (dealer-long-calls
    convention). by_strike is the net per strike, sorted by strike."""
    by, call, put = {}, 0.0, 0.0
    for o in chain:
        g, oi = o.get("gamma"), o.get("open_interest")
        if not g or not oi:
            continue
        val = g * oi * 100 * spot ** 2 * 0.01
        if o.get("option_type") == "put":
            val, put = -val, put - val
        else:
            call += val
        by[o["strike"]] = by.get(o["strike"], 0.0) + val
    return {"call_gex": call, "put_gex": put, "net_gex": call + put,
            "by_strike": [{"strike": k, "gex": round(v, 2)} for k, v in sorted(by.items())]}


SECTOR_ETFS = {"XLK": "Technology", "XLF": "Financials", "XLV": "Health Care",
               "XLY": "Consumer Discretionary", "XLP": "Consumer Staples", "XLE": "Energy",
               "XLI": "Industrials", "XLB": "Materials", "XLU": "Utilities",
               "XLRE": "Real Estate", "XLC": "Communication Services"}


def sector_heatmap(quotes):
    """SPDR sector-ETF quotes -> sectors ordered best to worst by % change."""
    rows = [{"symbol": s, "sector": SECTOR_ETFS[s], "change_pct": _change_pct(q)}
            for s, q in quotes.items()
            if s in SECTOR_ETFS and _change_pct(q) is not None]
    return sorted(rows, key=lambda r: r["change_pct"], reverse=True)
