"""What the options market is saying about one stock, from the full delayed chain: put/call ratios, contracts trading far above
their open interest, implied volatility by expiry, the move the market prices in, and put-versus-call skew."""

import math
from datetime import date


def option_flow(spot, chain, today_iso):
    today = date.fromisoformat(today_iso)
    rows = []
    for o in chain:
        dte = (date.fromisoformat(o["expiration"]) - today).days
        if dte >= 0:
            rows.append({**o, "dte": dte})
    if not rows or not spot:
        return None
    vol = lambda t: int(sum(o["volume"] or 0 for o in rows if o["option_type"] == t))
    oi = lambda t: int(sum(o["open_interest"] or 0 for o in rows if o["option_type"] == t))
    cv, pv, co, po = vol("call"), vol("put"), oi("call"), oi("put")

    unusual = []
    for o in rows:
        v, interest = o["volume"] or 0, o["open_interest"] or 0
        otm = o["strike"] >= spot if o["option_type"] == "call" else o["strike"] <= spot       # in-the-money premium is mostly intrinsic value
        if o["dte"] >= 1 and otm and v >= 500 and v >= 3 * max(interest, 1) and abs(o["strike"] - spot) / spot <= 0.3:
            mid = ((o["bid"] or 0) + (o["ask"] or 0)) / 2 if o.get("ask") else 0.0
            unusual.append({"type": o["option_type"], "strike": o["strike"], "expiration": o["expiration"], "dte": o["dte"], "volume": int(v),
                            "open_interest": int(interest), "premium": v * 100 * mid})
    unusual.sort(key=lambda u: -u["premium"])
    bias = sum(u["premium"] if u["type"] == "call" else -u["premium"] for u in unusual)

    exps = sorted({o["expiration"] for o in rows})
    term = []
    for e in exps[:6]:
        sub = [o for o in rows if o["expiration"] == e and (o["iv"] or 0) > 0]
        if not sub:
            continue
        k = min({o["strike"] for o in sub}, key=lambda s: abs(s - spot))
        ivs = [o["iv"] for o in sub if o["strike"] == k]
        term.append({"expiration": e, "dte": sub[0]["dte"], "atm_iv_pct": sum(ivs) / len(ivs) * 100})

    move = None
    for t in term:
        if t["dte"] >= 1:
            move = {"expiration": t["expiration"], "dte": t["dte"], "move": spot * t["atm_iv_pct"] / 100 * math.sqrt(t["dte"] / 365),
                    "move_pct": t["atm_iv_pct"] * math.sqrt(t["dte"] / 365)}
            break
    skew = None
    if term:
        pick = next((t for t in term if t["dte"] >= 20), term[-1])
        sub = [o for o in rows if o["expiration"] == pick["expiration"] and (o["iv"] or 0) > 0 and o.get("delta") is not None]
        puts = [o for o in sub if o["option_type"] == "put"]
        calls = [o for o in sub if o["option_type"] == "call"]
        if puts and calls:
            p = min(puts, key=lambda o: abs(o["delta"] + 0.25))
            c = min(calls, key=lambda o: abs(o["delta"] - 0.25))
            skew = {"expiration": pick["expiration"], "put_minus_call_pct": (p["iv"] - c["iv"]) * 100}

    pc = pv / cv if cv else None
    signals = []
    if pc is not None:
        tilt = "calls dominate: bullish tilt" if pc < 0.5 else "puts dominate: defensive or bearish tilt" if pc > 1.2 else "balanced"
        signals.append(f"Put/call volume ratio {pc:.2f}: {tilt}")
    for u in unusual[:3]:
        signals.append(f"Unusual {u['type']} activity: {u['volume']:,} contracts of the {u['strike']:g} {u['type']} expiring {u['expiration']} "
                       f"({u['volume'] / max(u['open_interest'], 1):.0f}x open interest, about ${u['premium'] / 1e6:.1f}M premium)")
    if move:
        signals.append(f"The market prices a move of about {move['move_pct']:.1f}% by {move['expiration']}")
    if skew and abs(skew["put_minus_call_pct"]) >= 5:
        signals.append(f"Puts cost {skew['put_minus_call_pct']:.0f} vol points more than calls at the same distance: investors pay up for protection"
                       if skew["put_minus_call_pct"] > 0 else "Calls cost more than puts at the same distance: upside is in demand")
    return {"call_volume": cv, "put_volume": pv, "pc_volume_ratio": pc, "call_oi": co, "put_oi": po,
            "pc_oi_ratio": po / co if co else None, "unusual": unusual[:6], "unusual_bias": bias, "term": term,
            "expected_move": move, "skew": skew, "signals": signals, "spot": spot, "as_of": today_iso}
