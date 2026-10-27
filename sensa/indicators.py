"""Chart indicators computed from OHLCV bars: moving averages (simple, exponential, volume-weighted), VWAP with
standard-deviation bands, EMA cloud, Bollinger bands, RSI and MACD. Plain functions on lists; `compute` returns
every series as [{"time", "value"}] ready for the chart. Bar times are epoch seconds (intraday) or YYYY-MM-DD (daily)."""

import math


def sma(x, n):
    out, run = [None] * len(x), 0.0
    for i, v in enumerate(x):
        run += v
        if i >= n:
            run -= x[i - n]
        if i >= n - 1:
            out[i] = run / n
    return out


def ema(x, n):
    """Exponential average seeded with the first n-value simple average; values before that are None."""
    out = [None] * len(x)
    if len(x) < n:
        return out
    a = 2 / (n + 1)
    prev = sum(x[:n]) / n
    out[n - 1] = prev
    for i in range(n, len(x)):
        prev = a * x[i] + (1 - a) * prev
        out[i] = prev
    return out


def vwma(price, vol, n):
    out = [None] * len(price)
    for i in range(n - 1, len(price)):
        v = sum(vol[i - n + 1:i + 1])
        out[i] = sum(p * w for p, w in zip(price[i - n + 1:i + 1], vol[i - n + 1:i + 1])) / v if v else None
    return out


def vwema(price, vol, n):
    num, den = ema([p * v for p, v in zip(price, vol)], n), ema(vol, n)
    return [a / b if a is not None and b else None for a, b in zip(num, den)]


def _series(bars, values):
    return [{"time": b["time"], "value": v} for b, v in zip(bars, values) if v is not None]


def _anchor_start(bars, anchor, mode):
    """Index of the first bar of each VWAP run: the anchor bar, each day (intraday), or the year start (daily)."""
    if anchor is not None:
        return {next((i for i, b in enumerate(bars) if b["time"] >= anchor), len(bars))}
    daily = bool(bars) and isinstance(bars[0]["time"], str)
    if (mode or ("year" if daily else "session")) == "year":
        if not bars:
            return set()
        year = str(bars[-1]["time"])[:4]
        return {next(i for i, b in enumerate(bars) if str(b["time"])[:4] == year)}
    starts, day = set(), None
    for i, b in enumerate(bars):
        d = b["time"] if isinstance(b["time"], str) else b["time"] // 86400
        if d != day:
            starts.add(i)
            day = d
    return starts


def vwap(bars, anchor=None, mode=None):
    """VWAP on the typical price with volume-weighted standard-deviation bands (1 and 2), plus the percent distance of
    the close from VWAP ("momentum"). `anchor` starts one run at that bar time; otherwise it restarts every day for
    intraday bars and runs from the start of the year for daily bars (mode "session" or "year" forces either)."""
    starts = _anchor_start(bars, anchor, mode)
    first = min(starts) if starts else 0
    keys = ("vwap", "upper1", "lower1", "upper2", "lower2", "momentum")
    out = {k: [] for k in keys}
    pv = p2v = vv = 0.0
    for i, b in enumerate(bars):
        if i < first:
            continue
        if i in starts:
            pv = p2v = vv = 0.0
        p = (b["high"] + b["low"] + b["close"]) / 3
        pv, p2v, vv = pv + p * b["volume"], p2v + p * p * b["volume"], vv + b["volume"]
        if not vv:
            continue
        m = pv / vv
        sd = math.sqrt(max(0.0, p2v / vv - m * m))
        t = b["time"]
        for k, v in (("vwap", m), ("upper1", m + sd), ("lower1", m - sd), ("upper2", m + 2 * sd), ("lower2", m - 2 * sd),
                     ("momentum", (b["close"] - m) / m * 100 if m else 0.0)):
            out[k].append({"time": t, "value": v})
    return out


def ema_cloud(close, fast=8, slow=21):
    f, s = ema(close, fast), ema(close, slow)
    return {"fast": f, "slow": s, "bullish": [None if a is None or b is None else a > b for a, b in zip(f, s)]}


def bollinger(x, n=20, k=2.0):
    mid = sma(x, n)
    up, lo = [None] * len(x), [None] * len(x)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        sd = math.sqrt(sum((v - mid[i]) ** 2 for v in w) / n)
        up[i], lo[i] = mid[i] + k * sd, mid[i] - k * sd
    return mid, up, lo


def rsi(x, n=14):
    out = [None] * len(x)
    if len(x) <= n:
        return out
    gains = [max(x[i] - x[i - 1], 0) for i in range(1, len(x))]
    losses = [max(x[i - 1] - x[i], 0) for i in range(1, len(x))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for i in range(n, len(x)):
        if i > n:
            ag, al = (ag * (n - 1) + gains[i - 1]) / n, (al * (n - 1) + losses[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def macd(x, fast=12, slow=26, signal=9):
    f, s = ema(x, fast), ema(x, slow)
    line = [None if a is None or b is None else a - b for a, b in zip(f, s)]
    start = next((i for i, v in enumerate(line) if v is not None), len(line))
    sig = [None] * start + ema([v for v in line[start:]], signal)
    return line, sig, [None if a is None or b is None else a - b for a, b in zip(line, sig)]


def compute(bars, anchor=None, mode=None):
    """Every indicator the chart can show, as {name: [{"time", "value"}]} (empty when there are too few bars)."""
    close = [b["close"] for b in bars]
    vol = [b["volume"] for b in bars]
    out = {f"sma{n}": _series(bars, sma(close, n)) for n in (20, 50, 200)}
    out["ema9"], out["ema21"] = _series(bars, ema(close, 9)), _series(bars, ema(close, 21))
    out["vwma20"], out["vwema20"] = _series(bars, vwma(close, vol, 20)), _series(bars, vwema(close, vol, 20))
    mid, up, lo = bollinger(close)
    out["bb_mid"], out["bb_upper"], out["bb_lower"] = _series(bars, mid), _series(bars, up), _series(bars, lo)
    out["rsi14"] = _series(bars, rsi(close))
    line, sig, hist = macd(close)
    out["macd"], out["macd_signal"], out["macd_hist"] = _series(bars, line), _series(bars, sig), _series(bars, hist)
    for k, v in vwap(bars, anchor, mode).items():
        out["vwap" if k == "vwap" else f"vwap_{k}"] = v
    c = ema_cloud(close)
    out["cloud_fast"], out["cloud_slow"] = _series(bars, c["fast"]), _series(bars, c["slow"])
    out["cloud_dir"] = _series(bars, [None if v is None else (1 if v else -1) for v in c["bullish"]])
    return out
