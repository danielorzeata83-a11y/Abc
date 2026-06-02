"""Build a self-contained HTML 'valuation thermometer' from Shiller CAPE.

Reads the monthly S&P 500 + PE10 data, computes the latest CAPE, its
historical percentile, and the CAPE-implied 10-year forward return, then
renders an SVG history chart (cheap/expensive zones) plus a summary card.

    python valuation_dashboard.py [--data data/sp500_monthly.csv]

A 10-year signal, not a market-timing tool. Not investment advice.
"""

import argparse
import os as _os
def _DATA(name):
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", name)

import numpy as np
import pandas as pd

from markov.valuation import valuation_label, percentile_rank, implied_forward_return

H = 120  # 10-year forward window (months)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=_DATA("sp500_monthly.csv"))
    ap.add_argument("--out", default="results/valuation_thermometer.html")
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    df = df[(df["SP500"] > 0) & (df["PE10"] > 0)].reset_index(drop=True)
    cape = df["PE10"].to_numpy()
    sp = df["SP500"].to_numpy()
    dates = df["Date"].astype(str).to_numpy()

    # forward 10y annualised return for the CAPE->return fit
    fwd = np.full(len(df), np.nan)
    for i in range(len(df) - H):
        fwd[i] = (sp[i + H] / sp[i]) ** (12 / H) - 1
    ok = ~np.isnan(fwd)

    cur = float(cape[-1])
    pct = percentile_rank(cur, cape)
    label = valuation_label(cur)
    implied = implied_forward_return(cur, cape[ok], fwd[ok])

    # --- SVG: CAPE history with zones ---
    W, Hpx, pad = 860, 320, 50
    cmax = float(np.nanmax(cape)) * 1.05
    def X(i): return pad + (W - 2 * pad) * i / (len(cape) - 1)
    def Y(v): return (Hpx - pad) - v / cmax * (Hpx - 2 * pad)
    def band(lo, hi, color):
        return (f'<rect x="{pad}" y="{Y(hi):.0f}" width="{W-2*pad}" '
                f'height="{Y(lo)-Y(hi):.0f}" fill="{color}" opacity="0.12"/>')
    pts = " ".join(f"{X(i):.1f},{Y(cape[i]):.1f}" for i in range(len(cape)))
    zones = (band(0, 15, "#1a7f37") + band(15, 25, "#9a6700")
             + band(25, cmax, "#cf222e"))
    cur_y = Y(cur)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hpx}" '
           f'font-family="system-ui" font-size="11">{zones}'
           f'<polyline points="{pts}" fill="none" stroke="#0969da" stroke-width="1.3"/>'
           f'<line x1="{pad}" y1="{cur_y:.0f}" x2="{W-pad}" y2="{cur_y:.0f}" '
           f'stroke="#cf222e" stroke-dasharray="4 3"/>'
           f'<text x="{W-pad-150}" y="{cur_y-5:.0f}" fill="#cf222e">acum CAPE {cur:.0f}</text>'
           f'<text x="{pad}" y="{Y(15)-3:.0f}" fill="#1a7f37">ieftin &lt;15</text>'
           f'<text x="{pad}" y="{Y(25)-3:.0f}" fill="#cf222e">scump &gt;25</text>'
           f'<text x="{pad}" y="{Hpx-12}">{dates[0][:4]}</text>'
           f'<text x="{W-pad-30}" y="{Hpx-12}">{dates[-1][:4]}</text></svg>')

    colour = {"CHEAP": "#1a7f37", "NORMAL": "#9a6700", "EXPENSIVE": "#cf222e"}[label]
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Termometru de valoare</title><style>body{{font-family:system-ui;
margin:2rem;max-width:900px}}.card{{background:#f6f8fa;border:1px solid #d0d7de;
border-radius:10px;padding:1.2rem;margin:1rem 0}}.big{{font-size:2rem;
font-weight:700;color:{colour}}}.warn{{color:#9a6700;background:#fff8c5;
border-color:#eac54f}}</style></head><body>
<h1>Termometru de valoare &mdash; S&amp;P 500 (CAPE)</h1>
<div class="card"><div class="big">{label} &middot; CAPE {cur:.1f}</div>
Mai scump dec&acirc;t <b>{pct:.0f}%</b> din istorie ({dates[0][:4]}&ndash;{dates[-1][:4]}).<br>
Randament implicat pe 10 ani (din istoric): <b>{implied*100:+.1f}%/an</b>.</div>
{svg}
<div class="card"><b>Cum citești:</b> verde = ieftin (be greedy), ro&#537;u = scump
(be fearful). Linia ro&#537;ie punctat&#259; = unde suntem acum.</div>
<div class="card warn">CAPE e semnal pe <b>10 ani</b>, NU pentru timing scurt &mdash;
scump poate r&#259;m&acirc;ne scump ani de zile. Folose&#537;te-l ca s&#259;-&#539;i temperezi
a&#537;tept&#259;rile &#537;i s&#259; cumperi mai agresiv c&acirc;nd pia&#539;a devine ieftin&#259;.
Sursa live: multpl.com/shiller-pe. NU este consiliere de investi&#539;ii.</div>
</body></html>"""

    import os as __os
    __os.makedirs(__os.path.dirname(__os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(html)
    print(f"CAPE {cur:.1f} ({label}) | percentila {pct:.0f}% | "
          f"randament implicat 10y {implied*100:+.1f}%/an")
    print(f"Thermometer written to {args.out}")


if __name__ == "__main__":
    main()
