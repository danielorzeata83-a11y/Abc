"""SVG renderer for the hindsight-vs-real-time trend overlay.

Draws four layers on one chart: the walk-forward HMM regime as background
bands, the price + SMA 50/200 lines, golden/death cross markers, the hindsight
bottom, and a lesson box (lag cost, whipsaws, drawdown). Visualisation only --
nothing here is investment advice.
"""

import numpy as np

from markov.svg_chart import scale_to_px, _x_px, _GREEN, _RED, _GREY
from markov.signal_engine import DISCLAIMER
from markov.states import State

_PRICE, _FAST, _SLOW = "#0969da", "#9a6700", "#8250df"
_BAND = {State.BULL: "#e6f4ea", State.SIDEWAYS: "#f0f0f0", State.BEAR: "#fde8e8"}


def _runs(states):
    """Compress a per-day state list into (start, end_exclusive, state) runs."""
    runs = []
    i, n = 0, len(states)
    while i < n:
        j = i
        while j < n and states[j] == states[i]:
            j += 1
        runs.append((i, j, states[i]))
        i = j
    return runs


def render_trend_svg(dates, close, sma_fast, sma_slow, crossovers,
                     states, state_start, bottom_idx, stats,
                     width=960, height=420, pad=52):
    close = np.asarray(close, dtype=float)
    n = len(close)
    left, right, top, bottom = pad, width - pad, 16, height - pad
    lo, hi = float(np.nanmin(close)), float(np.nanmax(close))
    span = (hi - lo) or 1.0
    vmin, vmax = lo - 0.05 * span, hi + 0.05 * span

    def X(i):
        return round(_x_px(i, n, left, right), 1)

    def Y(v):
        return round(scale_to_px(v, vmin, vmax, top, bottom), 1)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
             f'height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="system-ui,sans-serif" font-size="11">']

    # 1) regime background bands (walk-forward HMM, aligned at state_start)
    for a, b, st in _runs(states):
        x0 = X(state_start + a)
        x1 = X(state_start + b - 1)
        parts.append(f'<rect x="{x0}" y="{top}" width="{max(x1 - x0, 1)}" '
                     f'height="{bottom - top}" fill="{_BAND.get(st, "#ffffff")}"/>')

    # axis baseline + min/max labels
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" '
                 f'stroke="{_GREY}" stroke-width="1"/>')
    parts.append(f'<text x="{left}" y="{Y(vmax) - 4}" fill="{_GREY}">{vmax:.0f}</text>')
    parts.append(f'<text x="{left}" y="{bottom + 14}" fill="{_GREY}">{vmin:.0f}</text>')

    def _poly(series, color, dash=""):
        pts = " ".join(f"{X(i)},{Y(series[i])}"
                       for i in range(len(series)) if np.isfinite(series[i]))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<polyline points="{pts}" fill="none" stroke="{color}" '
                f'stroke-width="1.5"{d}/>')

    # 2) price + SMA lines
    parts.append(_poly(close, _PRICE))
    parts.append(_poly(np.asarray(sma_fast, dtype=float), _FAST, "5 3"))
    parts.append(_poly(np.asarray(sma_slow, dtype=float), _SLOW, "5 3"))

    # 3) hindsight bottom marker
    bx = X(bottom_idx)
    parts.append(f'<line x1="{bx}" y1="{top}" x2="{bx}" y2="{bottom}" '
                 f'stroke="{_GREEN}" stroke-width="1.5" stroke-dasharray="2 2"/>')
    parts.append(f'<text x="{bx + 3}" y="{top + 12}" fill="{_GREEN}">'
                 f'fund real {close[bottom_idx]:.0f} '
                 f'({str(dates[bottom_idx])[:10]})</text>')

    # 4) crossover markers
    for c in crossovers:
        cx, cy = X(c.idx), Y(close[c.idx])
        col = _GREEN if c.kind == "golden" else _RED
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{col}">'
                     f'<title>{c.kind.upper()} CROSS {str(dates[c.idx])[:10]} '
                     f'@ {close[c.idx]:.2f}</title></circle>')

    # lesson + drawdown box
    lines = [
        f"Golden {stats['fast']}/{stats['slow']} vs fundul real (hindsight):",
        f"cost intarziere: {stats['lag_cost'] * 100:+.0f}% pana la confirmare",
        f"semnale false (whipsaw): {stats['whipsaws']}",
        f"drawdown indurat dupa intrare: {stats['max_drawdown'] * 100:+.0f}%",
        DISCLAIMER,
    ]
    bx0, by0 = left + 6, top + 6
    parts.append(f'<rect x="{bx0}" y="{by0}" width="360" '
                 f'height="{14 * len(lines) + 12}" fill="#ffffff" '
                 f'fill-opacity="0.85" stroke="{_GREY}"/>')
    for k, ln in enumerate(lines):
        parts.append(f'<text x="{bx0 + 8}" y="{by0 + 18 + 14 * k}" '
                     f'fill="#24292f">{ln}</text>')

    parts.append("</svg>")
    return "\n".join(parts)
