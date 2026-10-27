"""Automatic top-N stocks and ETFs: a transparent composite of signals, with duplicates removed and inverse-volatility weights.

Stocks: the most widely held names of the top-100 funds, scored on price momentum (12-1 months), trend (above the 200-day
average is required), risk-adjusted return, fund buying, insider and House purchases. ETFs: a broad catalogue plus the
ETFs the funds hold, scored on momentum, trend, risk-adjusted return, drawdown and fund interest, at most three per
category. Research output, not investment advice."""

import re

import numpy as np

from sensa.picks_signals import (composite, insider_features, momentum_features, politician_features, smart_money_features, zscores)

NOTICE = ("Research output, not investment advice. The ranking is a rule-based screen on public data; it does not know your goals, "
          "taxes or risk tolerance, and past momentum and fund buying do not guarantee future returns.")

STOCK_WEIGHTS = {"momentum": 0.25, "trend": 0.10, "quality": 0.15, "smart": 0.30, "insider": 0.15, "politician": 0.05}
ETF_WEIGHTS = {"momentum": 0.35, "trend": 0.15, "quality": 0.25, "drawdown": 0.10, "smart": 0.15}

ETF_CATALOG = {
    "SPY": ("SPDR S&P 500", "us_equity"), "VOO": ("Vanguard S&P 500", "us_equity"), "IVV": ("iShares Core S&P 500", "us_equity"),
    "VTI": ("Vanguard Total US Market", "us_equity"), "QQQ": ("Invesco Nasdaq-100", "us_equity"), "IWM": ("iShares Russell 2000", "us_equity"),
    "DIA": ("SPDR Dow Jones", "us_equity"), "MDY": ("SPDR S&P MidCap 400", "us_equity"),
    "XLK": ("Technology Select Sector", "sector"), "XLF": ("Financial Select Sector", "sector"), "XLV": ("Health Care Select Sector", "sector"),
    "XLE": ("Energy Select Sector", "sector"), "XLY": ("Consumer Discretionary Select Sector", "sector"), "XLP": ("Consumer Staples Select Sector", "sector"),
    "XLI": ("Industrial Select Sector", "sector"), "XLU": ("Utilities Select Sector", "sector"), "XLB": ("Materials Select Sector", "sector"),
    "XLC": ("Communication Services Select Sector", "sector"), "SMH": ("VanEck Semiconductor", "sector"),
    "SCHD": ("Schwab US Dividend Equity", "factor"), "VIG": ("Vanguard Dividend Appreciation", "factor"), "MTUM": ("iShares MSCI USA Momentum", "factor"),
    "QUAL": ("iShares MSCI USA Quality", "factor"), "USMV": ("iShares MSCI USA Min Vol", "factor"),
    "EFA": ("iShares MSCI EAFE", "international"), "VEA": ("Vanguard FTSE Developed Markets", "international"),
    "VWO": ("Vanguard FTSE Emerging Markets", "international"), "EEM": ("iShares MSCI Emerging Markets", "international"),
    "AGG": ("iShares Core US Aggregate Bond", "bonds"), "BND": ("Vanguard Total Bond Market", "bonds"), "TLT": ("iShares 20+ Year Treasury", "bonds"),
    "IEF": ("iShares 7-10 Year Treasury", "bonds"), "LQD": ("iShares Investment Grade Corporate Bond", "bonds"), "HYG": ("iShares High Yield Corporate Bond", "bonds"),
    "TIP": ("iShares TIPS Bond", "bonds"), "GLD": ("SPDR Gold Shares", "commodities"), "SLV": ("iShares Silver Trust", "commodities"),
    "DBC": ("Invesco DB Commodity Index", "commodities"), "VNQ": ("Vanguard Real Estate", "real_estate"),
    "VUG": ("Vanguard Growth", "factor"), "VTV": ("Vanguard Value", "factor"), "VYM": ("Vanguard High Dividend Yield", "factor"),
    "VLUE": ("iShares MSCI USA Value Factor", "factor"), "IJR": ("iShares Core S&P Small-Cap", "us_equity"), "IJH": ("iShares Core S&P Mid-Cap", "us_equity"),
    "XBI": ("SPDR S&P Biotech", "sector"), "VGT": ("Vanguard Information Technology", "sector"), "IBB": ("iShares Biotechnology", "sector"),
    "VT": ("Vanguard Total World Stock", "international"),
}
_TRUST_NAME = re.compile(r"\b(TR|TRUST|SERIES TRUST|STRATEGIC TR|ETF TR)\s*$", re.I)
_LEVERAGED = re.compile(r"\b(ULTRA|ULTRAPRO|2X|3X|BEAR|SHORT|INVERSE|LEVERAGED|BULL)\b", re.I)
_CLASS_WORDS = {"CL", "CLASS", "COM", "CAP", "STK", "SHS", "ORD", "A", "B", "C", "NEW"}


def _company_key(issuer):
    w = re.sub(r"[^A-Z0-9 ]", " ", (issuer or "").upper()).split()
    while w and w[-1] in _CLASS_WORDS:
        w.pop()
    return " ".join(w[:3])


def _weights(vols, cap):
    inv = 1.0 / np.maximum(np.asarray(vols, dtype=float), 1e-6)
    w = inv / inv.sum()
    n = len(w)
    if n * cap < 1:
        return np.ones(n) / n
    for _ in range(50):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        w[under] += excess * w[under] / w[under].sum()
    return w


def _pct(x):
    return f"{x * 100:+.0f}%"


def _money(v):
    a = abs(v)
    s = f"${a / 1e9:.1f}B" if a >= 1e9 else f"${a / 1e6:.1f}M" if a >= 1e6 else f"${a / 1e3:.0f}k"
    return ("-" if v < 0 else "") + s


def _returns(closes, n=252):
    c = np.asarray(closes[-(n + 1):], dtype=float)
    return c[1:] / c[:-1] - 1


def _dedupe(ranked, keyfn, rets, corr_limit, notes):
    kept = []
    for item in ranked:
        dup = None
        for k in kept:
            if keyfn(item) and keyfn(item) == keyfn(k):
                dup = (k, "same company, other share class")
            else:
                a, b = rets[item["ticker"]], rets[k["ticker"]]
                n = min(len(a), len(b))
                if n > 60 and np.std(a[-n:]) > 0 and np.std(b[-n:]) > 0 and np.corrcoef(a[-n:], b[-n:])[0, 1] >= corr_limit:
                    dup = (k, f"near-duplicate of {k['ticker']} (return correlation above {corr_limit:.2f})")
            if dup:
                break
        if dup:
            notes.append(f"{item['ticker']} skipped: {dup[1]}" if dup[1].startswith("near") else f"{item['ticker']} skipped: {dup[1]} ({dup[0]['ticker']} ranks higher)")
        else:
            kept.append(item)
    return kept


def build_picks(overview, prices, insider_trades, politician_trades, top_n=10, pool_n=300, min_holders=10, min_price=5.0,
                max_weight=0.20, dedupe_corr=0.97, max_per_category=3, stock_weights=None, etf_weights=None):
    sw, ew = stock_weights or STOCK_WEIGHTS, etf_weights or ETF_WEIGHTS
    rows = overview["stocks"]
    ok = [s for s in rows if not s.get("gone") and not s.get("new_listing") and s["holders"] >= min_holders]
    ok.sort(key=lambda s: (s["holders"], s["value"]), reverse=True)
    stock_rows = [s for s in ok if s["kind"] in ("stock", "adr")][:pool_n]
    etf_rows = {s["ticker"]: s for s in ok if s["kind"] == "etf" and not _LEVERAGED.search(s.get("issuer", ""))}
    etf_pool = {**{t: {"name": n, "category": c} for t, (n, c) in ETF_CATALOG.items()},
                **{t: {"name": f"{t} (ETF held by funds)" if _TRUST_NAME.search(s["issuer"]) else s["issuer"].title(), "category": "other"}
                   for t, s in list(etf_rows.items())[:40] if t not in ETF_CATALOG}}
    prices.warm(sorted({s["ticker"] for s in stock_rows} | set(etf_pool) | {"SPY"}))
    ins, pol = insider_features(insider_trades), politician_features(politician_trades)
    notes, skipped, skipped_etf = [], {"no_history": 0, "low_price": 0, "downtrend": 0}, {"no_history": 0, "low_price": 0, "downtrend": 0}
    as_of = [None]

    def collect(tickers, counter):
        out = {}
        for t in tickers:
            hist = prices.closes(t)
            f = momentum_features(hist[1]) if hist else None
            if f is None:
                counter["no_history"] += 1
                continue
            if hist[1][-1] < min_price:
                counter["low_price"] += 1
                continue
            if f["trend"] < 1.0:
                counter["downtrend"] += 1
                continue
            out[t] = {"f": f, "closes": hist[1], "last_date": hist[0][-1]}
            as_of[0] = max(as_of[0] or "", hist[0][-1])
        return out

    # ---------------------------------------------------------------- stocks
    srow = {s["ticker"]: s for s in stock_rows}
    data = collect(list(srow), skipped)
    sm = {t: smart_money_features(srow[t]) for t in data}

    def insider_score(t):
        x = ins.get(t)
        return 0.0 if not x else float(np.sign(x["net"]) * np.log1p(abs(x["net"]) / 1e5) + 0.5 * x["buyers"])
    sig = {"momentum": zscores({t: d["f"]["ret_12_1"] for t, d in data.items()}), "trend": zscores({t: d["f"]["trend"] for t, d in data.items()}),
           "quality": zscores({t: d["f"]["sharpe"] for t, d in data.items()}),
           "insider": zscores({t: insider_score(t) for t in data}),
           "politician": zscores({t: float(pol.get(t, {}).get("net", 0)) for t in data})}
    hz, fz = zscores({t: sm[t]["holders_change"] for t in data}), zscores({t: sm[t]["flow"] for t in data})
    sig["smart"] = {t: (None if hz[t] is None else 0.5 * hz[t] + 0.5 * fz[t]) for t in data}
    scored = []
    for t, d in data.items():
        z = {k: sig[k][t] for k in sig}
        sc = composite(z, sw, min_signals=4)
        if sc is None:
            continue
        r, f, s = srow[t], d["f"], sm[t]
        reasons = [f"Held by {r['holders']} of the top funds ({r['holders'] - r['holders_prev']:+d} vs last quarter)"
                   + (f", active fund buying {_money(r['active_flow'])}" if r["active_flow"] > 0 else "")
                   + (f", {r['new']} funds opened positions" if r.get("new") else ""),
                   f"Price {_pct(f['ret_12_1'])} over 12 months (last month excluded), above its 200-day average"]
        if f["ret_12_1"] > 1.5:
            reasons.append(f"Very extended: {_pct(f['ret_12_1'])} in a year; sharp pullbacks are common after moves like this")
        if ins.get(t) and ins[t]["buyers"]:
            reasons.append(f"{ins[t]['buyers']} insider{'s' if ins[t]['buyers'] > 1 else ''} bought, net {_money(ins[t]['net'])} in the last 90 days")
        if pol.get(t) and pol[t]["buyers"]:
            reasons.append(f"{pol[t]['buyers']} House member{'s' if pol[t]['buyers'] > 1 else ''} bought")
        scored.append({"ticker": t, "name": r["issuer"].title(), "score": float(sc), "price": float(d["closes"][-1]),
                       "signals": {k: (None if v is None else round(float(v), 2)) for k, v in z.items()},
                       "features": {"ret_12_1": f["ret_12_1"], "ret_1m": f["ret_1m"], "vol": f["vol"], "drawdown": f["drawdown"]},
                       "reasons": reasons, "_closes": d["closes"], "_issuer": r["issuer"]})
    scored.sort(key=lambda x: -x["score"])
    rets = {p["ticker"]: _returns(p["_closes"]) for p in scored}
    picks = _dedupe(scored, lambda p: _company_key(p["_issuer"]), rets, dedupe_corr, notes)[:top_n]
    stocks = _finish(picks)

    # ------------------------------------------------------------------ ETFs
    edata = collect(list(etf_pool), skipped_etf)
    ez = {"momentum": zscores({t: d["f"]["ret_12_1"] for t, d in edata.items()}), "trend": zscores({t: d["f"]["trend"] for t, d in edata.items()}),
          "quality": zscores({t: d["f"]["sharpe"] for t, d in edata.items()}), "drawdown": zscores({t: d["f"]["drawdown"] for t, d in edata.items()})}
    interest = {t: smart_money_features(etf_rows[t])["holders_change"] for t in edata if t in etf_rows}
    iz = zscores(interest) if interest else {}
    escored = []
    for t, d in edata.items():
        z = {k: ez[k][t] for k in ez}
        z["smart"] = iz.get(t)
        sc = composite(z, ew, min_signals=3)
        if sc is None:
            continue
        f = d["f"]
        reasons = [f"Price {_pct(f['ret_12_1'])} over 12 months (last month excluded), above its 200-day average",
                   f"Volatility {f['vol'] * 100:.0f}% a year, {abs(f['drawdown']) * 100:.0f}% below its 52-week high"]
        if t in etf_rows:
            r = etf_rows[t]
            reasons.append(f"Held by {r['holders']} of the top funds ({r['holders'] - r['holders_prev']:+d} vs last quarter)")
        escored.append({"ticker": t, "name": etf_pool[t]["name"], "category": etf_pool[t]["category"], "score": float(sc), "price": float(d["closes"][-1]),
                        "signals": {k: (None if v is None else round(float(v), 2)) for k, v in z.items()},
                        "features": {"ret_12_1": f["ret_12_1"], "ret_1m": f["ret_1m"], "vol": f["vol"], "drawdown": f["drawdown"]},
                        "reasons": reasons, "_closes": d["closes"]})
    escored.sort(key=lambda x: -x["score"])
    erets = {p["ticker"]: _returns(p["_closes"]) for p in escored}
    unique = _dedupe(escored, lambda p: None, erets, 0.985, notes)
    per, chosen = {}, []
    for p in unique:
        if per.get(p["category"], 0) >= max_per_category:
            notes.append(f"{p['ticker']} skipped: already {max_per_category} {p['category'].replace('_', ' ')} ETFs in the list")
            continue
        per[p["category"]] = per.get(p["category"], 0) + 1
        chosen.append(p)
        if len(chosen) == top_n:
            break
    etfs = _finish(chosen)
    pool_prices = {"stocks": {p["ticker"]: p["price"] for p in scored}, "etfs": {p["ticker"]: p["price"] for p in escored}}
    return {"notice": NOTICE, "as_of": as_of[0], "stocks": stocks, "etfs": etfs, "pool_prices": pool_prices, "skipped": skipped, "skipped_etf": skipped_etf,
            "skipped_notes": notes[:40], "quarter": overview.get("quarter"),
            "pool": {"stocks": len(stock_rows), "etfs": len(etf_pool), "stocks_scored": len(scored), "etfs_scored": len(escored)},
            "method": {"stock_weights": sw, "etf_weights": ew, "trend_rule": "price above its 200-day average", "min_price": min_price,
                       "max_weight": max_weight, "weighting": "inverse volatility, capped", "dedupe_corr": dedupe_corr,
                       "max_per_category": max_per_category}}


def _finish(picks, max_weight=0.20):
    if not picks:
        return []
    w = _weights([p["features"]["vol"] for p in picks], max_weight)
    for i, p in enumerate(picks):
        p["rank"], p["weight"] = i + 1, float(w[i])
        p.pop("_closes", None)
        p.pop("_issuer", None)
    return picks
