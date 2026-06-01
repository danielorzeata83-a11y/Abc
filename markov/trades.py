"""Discrete trade simulator: turn a signal timeline into entry/SL/TP/exit.

This is a VISUALISATION/INTERPRETATION layer on top of the continuous
cross-sectional signals -- it imposes a discrete-trade framework (fixed-%
stop-loss / take-profit) so a chart can show where an order entered, where
the stop and target sat, and how the trade ended. It is NOT a validated
strategy (the project's edges are continuous portfolios; see REPORT.md).

A long opens when the signal exceeds +threshold while flat; a short when it
drops below -threshold. The position is then managed bar by bar: exit at the
stop, the target, a signal flip, or after max_hold bars.
"""

from dataclasses import dataclass


@dataclass
class Trade:
    side: str            # 'long' or 'short'
    entry_idx: int
    entry_date: object
    entry_px: float
    sl: float
    tp: float
    exit_idx: int
    exit_date: object
    exit_px: float
    reason: str          # 'TP' | 'SL' | 'flip' | 'timeout' | 'end'
    ret: float           # signed trade return
    r_multiple: float    # ret / risk (risk = sl distance)


def _close_trade(side, ei, edate, epx, sl, tp, xi, xdate, xpx, reason, risk):
    ret = (xpx / epx - 1.0) if side == "long" else (epx / xpx - 1.0)
    r_mult = ret / risk if risk > 0 else 0.0
    return Trade(side, ei, edate, epx, sl, tp, xi, xdate, xpx, reason,
                 ret, r_mult)


def simulate_trades(dates, high, low, close, signal, threshold=0.15,
                    sl_pct=0.05, tp_pct=0.10, max_hold=20):
    """Simulate discrete trades from a per-bar signal. Returns list[Trade]."""
    n = len(close)
    trades = []
    i = 0
    while i < n:
        s = signal[i]
        if s > threshold:
            side = "long"
        elif s < -threshold:
            side = "short"
        else:
            i += 1
            continue

        epx = float(close[i])
        if side == "long":
            sl, tp = epx * (1 - sl_pct), epx * (1 + tp_pct)
        else:
            sl, tp = epx * (1 + sl_pct), epx * (1 - tp_pct)
        ei, edate = i, dates[i]

        j = i + 1
        closed = None
        while j < n:
            hi, lo, cl = float(high[j]), float(low[j]), float(close[j])
            if side == "long":
                if lo <= sl:
                    closed = (j, sl, "SL"); break
                if hi >= tp:
                    closed = (j, tp, "TP"); break
                if signal[j] < -threshold:
                    closed = (j, cl, "flip"); break
            else:
                if hi >= sl:
                    closed = (j, sl, "SL"); break
                if lo <= tp:
                    closed = (j, tp, "TP"); break
                if signal[j] > threshold:
                    closed = (j, cl, "flip"); break
            if j - ei >= max_hold:
                closed = (j, cl, "timeout"); break
            j += 1
        if closed is None:  # ran off the end while open
            closed = (n - 1, float(close[n - 1]), "end")

        xi, xpx, reason = closed
        trades.append(_close_trade(side, ei, edate, epx, sl, tp, xi,
                                    dates[xi], xpx, reason, sl_pct))
        i = xi + 1  # look for the next trade after this one closes
    return trades
