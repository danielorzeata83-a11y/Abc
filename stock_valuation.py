"""Per-stock valuation context dashboard (HTML).

Input a ticker; shows its valuation ratios (P/E, P/B, P/S, dividend yield)
versus its sector and the whole market, with relative-cheapness bars and a
label. This is valuation CONTEXT, not a validated buy signal -- per-stock
valuation lacks the index-level CAPE->return evidence.

    python stock_valuation.py --ticker AAPL

Not investment advice.
"""

import argparse
import os as _os
def _DATA(name):
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", name)

import numpy as np
import pandas as pd

from markov.fundamentals import valuation_context, cheaper_than_pct, RATIOS


def _bar(pct, label):
    if not np.isfinite(pct):
        return f"<div>{label}: n/a</div>"
    colour = "#1a7f37" if pct >= 66 else ("#cf222e" if pct <= 33 else "#9a6700")
    return (f"<div style='margin:.3rem 0'>{label}: <b>{pct:.0f}%</b> mai ieftin"
            f"<div style='background:#e7ecf0;border-radius:4px;height:10px;width:320px'>"
            f"<div style='background:{colour};height:10px;border-radius:4px;"
            f"width:{max(2,pct)*3.2:.0f}px'></div></div></div>")


def render(df, ctx):
    sector_df = df[df["Sector"] == ctx["sector"]]
    rows = ""
    for r in RATIOS:
        v = ctx["ratios"][r]
        smed = sector_df[r].median()
        mmed = df[r].median()
        vtxt = f"{v:.1f}" if v else "n/a"
        rows += (f"<tr><td>{r}</td><td><b>{vtxt}</b></td>"
                 f"<td>{smed:.1f}</td><td>{mmed:.1f}</td>"
                 f"<td>{cheaper_than_pct(v, sector_df[r].to_numpy()):.0f}%</td></tr>")
    dy = ctx["dividend_yield"]
    colour = {"CHEAP vs sector": "#1a7f37", "NORMAL vs sector": "#9a6700",
              "EXPENSIVE vs sector": "#cf222e"}[ctx["label"]]
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{ctx['ticker']} valuation</title><style>body{{font-family:system-ui;
margin:2rem;max-width:760px}}table{{border-collapse:collapse;margin:1rem 0}}
td,th{{padding:.4rem .8rem;border-bottom:1px solid #eee;text-align:left}}
.card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;
padding:1.2rem;margin:1rem 0}}.big{{font-size:1.6rem;font-weight:700;color:{colour}}}
.warn{{color:#9a6700;background:#fff8c5;border-color:#eac54f}}</style></head><body>
<h1>{ctx['ticker']} &mdash; context de valoare</h1>
<div class="card"><div class="big">{ctx['label']}</div>
Sector: {ctx['sector']} &middot; P/E {ctx['pe']:.1f}
{' &middot; randament dividend '+f"{dy*100:.1f}%" if dy else ''}<br>
Mai ieftin dec&acirc;t <b>{ctx['sector_cheaper_pct']:.0f}%</b> din sector,
<b>{ctx['market_cheaper_pct']:.0f}%</b> din pia&#539;&#259;.</div>
<table><thead><tr><th>Ratio</th><th>{ctx['ticker']}</th><th>mediana sector</th>
<th>mediana pia&#539;&#259;</th><th>mai ieftin ca</th></tr></thead><tbody>{rows}</tbody></table>
<div class="card">{_bar(ctx['sector_cheaper_pct'],'vs sector')}
{_bar(ctx['market_cheaper_pct'],'vs pia&#539;&#259;')}</div>
<div class="card warn"><b>Aten&#539;ie:</b> acesta e CONTEXT de valoare (rela&#539;ie cu
sectorul/pia&#539;a), NU un semnal de cump&#259;rare validat. Spre deosebire de CAPE
pe indice (cu dovad&#259; randament pe 10 ani), valoarea pe o ac&#539;iune individual&#259;
NU are edge dovedit &mdash; ieftin poate r&#259;m&acirc;ne ieftin (value trap). Snapshot,
nu serie temporal&#259;. NU este consiliere de investi&#539;ii.</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--universe", default=_DATA("sp500_financials.csv"),
                    help="peer-universe snapshot CSV (for sector/market percentiles)")
    ap.add_argument("--provider", default=None,
                    help="optional live refresh of the target, e.g. fmp:API_KEY")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    ticker = args.ticker.upper()

    # Peer universe (needed for sector/market percentiles) from the snapshot.
    df = pd.read_csv(args.universe)

    # Optional: refresh just the target ticker with live data.
    if args.provider:
        from markov.fundamentals_provider import get_fundamentals_provider
        from markov.data_providers import DataUnavailable
        try:
            live = get_fundamentals_provider(args.provider).fetch([ticker])
            df = pd.concat([df[df["Symbol"] != ticker], live],
                           ignore_index=True)
            print(f"(refreshed {ticker} live via {args.provider.split(':')[0]})")
        except (DataUnavailable, Exception) as exc:
            print(f"(live refresh failed: {exc}; using snapshot)")

    ctx = valuation_context(df, ticker)
    out = args.out or f"results/{ticker}_valuation.html"
    import os as __os
    __os.makedirs(__os.path.dirname(__os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(df, ctx))
    print(f"{ctx['ticker']}: {ctx['label']} | P/E {ctx['pe']:.1f} | "
          f"cheaper than {ctx['sector_cheaper_pct']:.0f}% of {ctx['sector']}")
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
