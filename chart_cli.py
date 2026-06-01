"""Render a single-ticker chart with full trade history (entry/SL/TP/exit).

Computes the ticker's combined cross-sectional signal over time (reversal +
residual-momentum + illiquidity rank, at rebalance frequency), turns it into
discrete fixed-% SL/TP trades, and writes a self-contained HTML page: an SVG
price chart with trade markers, a legend explaining BUY/SELL/SL/TP/R, a
trade table, and summary stats.

    python chart_cli.py --ticker NVDA --data data/sp500.csv

The discrete SL/TP trades are a VISUALISATION overlay on the continuous
signals, NOT a validated strategy. Nothing here is investment advice.
"""

import argparse

import numpy as np
import pandas as pd

from markov import xs_signals as xs
from markov.trades import simulate_trades
from markov.svg_chart import render_price_svg
from markov.signal_engine import DISCLAIMER

LEGEND = [
    ("BUY (long)", "signal above threshold -> enter long at the close"),
    ("SELL (short)", "signal below -threshold -> enter short"),
    ("TP (green dashed)", "take-profit level; exit in profit if price reaches it"),
    ("SL (red dashed)", "stop-loss level; exit at a loss if price reaches it"),
    ("R multiple", "profit/loss measured in units of risk (the stop distance)"),
]


def load_ohlc(path, ticker):
    raw = pd.read_csv(path)
    def w(col):
        return raw.pivot(index="date", columns="Name", values=col).sort_index()
    close = w("close").dropna(axis=1)
    cols = list(close.columns)
    if ticker not in cols:
        raise SystemExit(f"{ticker} not in {path}")
    dates = pd.to_datetime(close.index).to_numpy()
    high = w("high")[cols].to_numpy()
    low = w("low")[cols].to_numpy()
    volume = w("volume")[cols].to_numpy().astype(float)
    return dates, close.to_numpy(), high, low, volume, cols.index(ticker)


def signal_timeline(prices, volume, idx, holding=5, threshold=0.15):
    """Per-bar combined cross-sectional position for the target ticker."""
    T = prices.shape[0]
    pos = np.zeros(T)
    start = 148  # residual momentum warmup (lookback 126 + skip 21 + 1)
    for t in range(start, T, holding):
        parts = [xs.reversal_position(prices[:t + 1], idx, lookback=10),
                 xs.resmom_position(prices[:t + 1], idx)]
        if volume is not None:
            parts.append(xs.amihud_position(prices[:t + 1], volume[:t + 1], idx))
        pos[t:t + holding] = float(np.mean(parts))
    return pos


def summarise(trades):
    if not trades:
        return "No trades generated."
    wins = [t for t in trades if t.ret > 0]
    avg_r = np.mean([t.r_multiple for t in trades])
    total = np.prod([1 + t.ret for t in trades]) - 1
    return (f"{len(trades)} trades | win rate {len(wins)/len(trades)*100:.0f}% "
            f"| avg {avg_r:+.2f}R | compounded {total*100:+.0f}% "
            f"(unlevered, sequential)")


def render_html(ticker, dates, close, trades, sl_pct, tp_pct):
    svg = render_price_svg(dates, close, trades)
    legend = "".join(f"<li><b>{k}</b> &mdash; {v}</li>" for k, v in LEGEND)
    rows = "".join(
        f"<tr><td>{t.side}</td><td>{str(t.entry_date)[:10]}</td>"
        f"<td>{t.entry_px:.2f}</td><td>{str(t.exit_date)[:10]}</td>"
        f"<td>{t.exit_px:.2f}</td><td>{t.reason}</td>"
        f"<td style='color:{'#1a7f37' if t.ret>0 else '#cf222e'}'>"
        f"{t.ret*100:+.1f}%</td><td>{t.r_multiple:+.2f}R</td></tr>"
        for t in trades)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{ticker} trades</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;max-width:960px}}
table{{border-collapse:collapse;font-size:.9rem}}td,th{{padding:.3rem .7rem;
border-bottom:1px solid #eee;text-align:left}}.box{{background:#f6f8fa;
border:1px solid #d0d7de;border-radius:8px;padding:1rem;margin:1rem 0}}
.warn{{color:#9a6700;background:#fff8c5;border-color:#eac54f}}
ul{{line-height:1.7}}</style></head><body>
<h1>{ticker} &mdash; signal trades (SL {sl_pct*100:.0f}% / TP {tp_pct*100:.0f}%)</h1>
<div class="box"><b>Summary:</b> {summarise(trades)}</div>
{svg}
<div class="box"><b>How to read this chart</b><ul>{legend}</ul>
Triangle = entry (up=long, down=short); circle = exit (green=win, red=loss);
hover any marker for details.</div>
<h3>Trades</h3>
<table><thead><tr><th>Side</th><th>Entry</th><th>@</th><th>Exit</th><th>@</th>
<th>Reason</th><th>Return</th><th>R</th></tr></thead><tbody>{rows}</tbody></table>
<div class="box warn">The discrete SL/TP trades are a VISUALISATION overlay on
the continuous cross-sectional signals &mdash; NOT a validated strategy
(see results/REPORT.md). {DISCLAIMER}</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--data", default="data/sp500.csv")
    ap.add_argument("--sl", type=float, default=0.05)
    ap.add_argument("--tp", type=float, default=0.10)
    ap.add_argument("--max-hold", type=int, default=20)
    ap.add_argument("--threshold", type=float, default=0.15)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    dates, close, high, low, volume, idx = load_ohlc(args.data, args.ticker)
    sig = signal_timeline(close, volume, idx, threshold=args.threshold)
    trades = simulate_trades(dates, high[:, idx], low[:, idx], close[:, idx],
                             sig, threshold=args.threshold, sl_pct=args.sl,
                             tp_pct=args.tp, max_hold=args.max_hold)
    out = args.out or f"results/{args.ticker}_chart.html"
    with open(out, "w") as fh:
        fh.write(render_html(args.ticker, dates, close[:, idx], trades,
                             args.sl, args.tp))
    print(summarise(trades))
    print(f"Chart written to {out}")


if __name__ == "__main__":
    main()
