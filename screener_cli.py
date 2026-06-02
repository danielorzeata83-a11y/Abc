"""Value+quality screener dashboard.

Scores every stock on value (cheap vs sector) and quality (EBITDA margin vs
sector), assigns a quadrant, and renders an HTML table highlighting
CHEAP + QUALITY candidates and flagging value traps. Filter by --quadrant.

    python screener_cli.py
    python screener_cli.py --quadrant "CHEAP + QUALITY"

Context for judgement, not a validated buy signal. Not investment advice.
"""

import argparse

import numpy as np
import pandas as pd

from markov.screener import compute_scores, QUADRANTS
from markov.fundamentals_provider import get_fundamentals_provider
from markov.data_providers import DataUnavailable

COLOUR = {
    "CHEAP + QUALITY": "#1a7f37",
    "CHEAP but LOW QUALITY (trap risk)": "#cf222e",
    "QUALITY but PRICEY": "#9a6700",
    "EXPENSIVE + LOW QUALITY (avoid)": "#6e7781",
    "n/a": "#6e7781",
}


def render(df, focus):
    df = df.sort_values(["value_pct", "quality_pct"], ascending=False)
    if focus:
        df = df[df["quadrant"] == focus]
    rows = ""
    for _, r in df.head(60).iterrows():
        dy = f"{r['Dividend Yield']*100:.1f}%" if pd.notna(r["Dividend Yield"]) else "-"
        mg = f"{r['EBITDA Margin']*100:.0f}%" if np.isfinite(r["EBITDA Margin"]) else "-"
        rows += (f"<tr><td><b>{r['Symbol']}</b></td><td>{r['Sector'][:22]}</td>"
                 f"<td>{r['Price/Earnings']:.1f}</td><td>{mg}</td><td>{dy}</td>"
                 f"<td>{r['value_pct']:.0f}</td><td>{r['quality_pct']:.0f}</td>"
                 f"<td style='color:{COLOUR.get(r['quadrant'],'#000')};font-weight:600'>"
                 f"{r['quadrant']}</td></tr>")
    counts = df["quadrant"].value_counts().to_dict() if not focus else {}
    summary = " &middot; ".join(f"{k}: {v}" for k, v in counts.items())
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Value + Quality screener</title><style>body{{font-family:system-ui;
margin:2rem;max-width:1000px}}table{{border-collapse:collapse;font-size:.85rem}}
td,th{{padding:.35rem .6rem;border-bottom:1px solid #eee;text-align:left}}
.card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;padding:1rem;
margin:1rem 0}}.warn{{color:#9a6700;background:#fff8c5;border-color:#eac54f}}</style>
</head><body><h1>Value + Quality screener{(' &mdash; '+focus) if focus else ''}</h1>
<div class="card">Idea: cheap is only good if the business is sound. <b>CHEAP +
QUALITY</b> = candidate; <b>CHEAP + LOW QUALITY</b> = value-trap risk. {summary}</div>
<table><thead><tr><th>Ticker</th><th>Sector</th><th>P/E</th><th>EBITDA mg</th>
<th>Div</th><th>value%</th><th>quality%</th><th>quadrant</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="card warn">Valuation CONTEXT, not a validated buy signal. Per-stock
value lacks the index CAPE&rarr;return evidence; combine with your own research.
Snapshot data. NOT investment advice.</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="csv:data/sp500_financials.csv",
                    help="csv:PATH or fmp:API_KEY")
    ap.add_argument("--tickers", default=None, help="comma list (live providers)")
    ap.add_argument("--quadrant", default=None, choices=list(QUADRANTS) + [None])
    ap.add_argument("--out", default="results/screener.html")
    args = ap.parse_args()
    tickers = args.tickers.split(",") if args.tickers else None
    try:
        raw = get_fundamentals_provider(args.provider).fetch(tickers)
    except DataUnavailable as exc:
        raise SystemExit(str(exc))
    df = compute_scores(raw)
    with open(args.out, "w") as fh:
        fh.write(render(df, args.quadrant))
    cq = df[df["quadrant"] == "CHEAP + QUALITY"].sort_values("value_pct", ascending=False)
    print(f"{len(df)} stocks scored | CHEAP + QUALITY: {len(cq)}")
    print("Top candidates:", ", ".join(cq["Symbol"].head(8)))
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
