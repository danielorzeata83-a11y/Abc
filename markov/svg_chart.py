"""Zero-dependency SVG price chart with trade overlays.

Renders a price line plus, for each Trade, an entry triangle, an exit
circle, and stop-loss (red) / take-profit (green) reference segments, with
native <title> hover tooltips. Pure string building -- no libraries, no
network, fully self-contained for embedding in an HTML page.
"""

import numpy as np

_RED, _GREEN, _BLUE, _GREY = "#cf222e", "#1a7f37", "#0969da", "#6e7781"


def scale_to_px(value, vmin, vmax, top, bottom):
    """Map a data value to a y pixel (vmax->top, vmin->bottom)."""
    if vmax == vmin:
        return (top + bottom) / 2
    frac = (value - vmin) / (vmax - vmin)
    return bottom - frac * (bottom - top)


def _x_px(i, n, left, right):
    if n <= 1:
        return left
    return left + (right - left) * i / (n - 1)


def render_price_svg(dates, close, trades, width=900, height=380,
                     pad=48):
    close = np.asarray(close, dtype=float)
    n = len(close)
    left, right, top, bottom = pad, width - pad, 16, height - pad
    lo, hi = float(np.min(close)), float(np.max(close))
    # pad the value range a touch so markers don't clip
    span = (hi - lo) or 1.0
    vmin, vmax = lo - 0.05 * span, hi + 0.05 * span

    def X(i):
        return round(_x_px(i, n, left, right), 1)

    def Y(v):
        return round(scale_to_px(v, vmin, vmax, top, bottom), 1)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
             f'height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="system-ui,sans-serif" font-size="11">']
    # axes
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" '
                 f'stroke="{_GREY}" stroke-width="1"/>')
    parts.append(f'<text x="{left}" y="{Y(vmax)-4}" fill="{_GREY}">{vmax:.2f}</text>')
    parts.append(f'<text x="{left}" y="{bottom+14}" fill="{_GREY}">{vmin:.2f}</text>')

    # price polyline
    pts = " ".join(f"{X(i)},{Y(close[i])}" for i in range(n))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{_BLUE}" '
                 f'stroke-width="1.5"/>')

    # trade overlays
    for t in trades:
        x0, x1 = X(t.entry_idx), X(t.exit_idx)
        ec = _GREEN if t.ret > 0 else _RED
        # SL / TP reference segments across the trade's span
        parts.append(f'<line x1="{x0}" y1="{Y(t.tp)}" x2="{x1}" y2="{Y(t.tp)}" '
                     f'stroke="{_GREEN}" stroke-width="1" stroke-dasharray="4 3"/>')
        parts.append(f'<line x1="{x0}" y1="{Y(t.sl)}" x2="{x1}" y2="{Y(t.sl)}" '
                     f'stroke="{_RED}" stroke-width="1" stroke-dasharray="4 3"/>')
        # entry triangle (points up for long, down for short)
        ey = Y(t.entry_px)
        if t.side == "long":
            tri = f"{x0},{ey-7} {x0-6},{ey+5} {x0+6},{ey+5}"
        else:
            tri = f"{x0},{ey+7} {x0-6},{ey-5} {x0+6},{ey-5}"
        parts.append(f'<polygon points="{tri}" fill="{_BLUE}">'
                     f'<title>{t.side.upper()} entry {str(t.entry_date)[:10]} '
                     f'@ {t.entry_px:.2f}\nSL {t.sl:.2f}  TP {t.tp:.2f}</title>'
                     f'</polygon>')
        # exit circle, coloured by outcome
        parts.append(f'<circle cx="{x1}" cy="{Y(t.exit_px)}" r="4" fill="{ec}">'
                     f'<title>EXIT {str(t.exit_date)[:10]} @ {t.exit_px:.2f} '
                     f'({t.reason}) {t.ret*100:+.1f}%  {t.r_multiple:+.2f}R</title>'
                     f'</circle>')

    parts.append("</svg>")
    return "\n".join(parts)
