"""Dashboard rendering: rank a set of Signals and render text/HTML views.

Pure functions over a list of Signal objects so they are easy to test;
the I/O wrapper lives in the root dashboard.py CLI.
"""

from markov.signal_engine import DISCLAIMER


def rank_signals(signals):
    """Signals sorted by position descending (strongest BUY first)."""
    return sorted(signals, key=lambda s: s.position, reverse=True)


def _select(signals, top_n):
    ranked = rank_signals(signals)
    if top_n is None:
        return ranked
    # Strongest buys (top) and strongest sells (bottom).
    return ranked[:top_n] + ranked[-top_n:] if len(ranked) > 2 * top_n else ranked


def render_table(signals, top_n=None):
    """Plain-text table of ticker / signal / position / confidence."""
    rows = _select(signals, top_n)
    out = [f"{'TICKER':<8}{'SIGNAL':<6}{'POS':>7}{'CONF':>7}"]
    out.append("-" * 28)
    for s in rows:
        out.append(f"{s.ticker:<8}{s.label:<6}{s.position:>+7.2f}{s.confidence:>7.2f}")
    out.append("-" * 28)
    out.append(DISCLAIMER)
    return "\n".join(out)


def render_html(signals, title="Signals", top_n=None):
    """Minimal standalone HTML dashboard."""
    rows = _select(signals, top_n)
    colour = {"BUY": "#1a7f37", "SELL": "#cf222e", "HOLD": "#6e7781"}
    trs = []
    for s in rows:
        c = colour.get(s.label, "#000")
        trs.append(
            f"<tr><td>{s.ticker}</td>"
            f"<td style='color:{c};font-weight:600'>{s.label}</td>"
            f"<td>{s.position:+.2f}</td><td>{s.confidence:.2f}</td></tr>"
        )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}
table{{border-collapse:collapse}}td,th{{padding:.3rem .8rem;border-bottom:1px solid #ddd;text-align:left}}
.note{{color:#6e7781;font-size:.85rem;margin-top:1rem}}</style></head>
<body><h1>{title}</h1>
<table><thead><tr><th>Ticker</th><th>Signal</th><th>Pos</th><th>Conf</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
<p class="note">{DISCLAIMER}</p></body></html>"""
