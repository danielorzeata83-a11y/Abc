"""DCA planner that uses the CAPE-implied return — connects both tools.

The CAPE thermometer says how expensive the market is and what 10-year
return history implies from here; this planner projects your monthly DCA
forward at that implied rate (plus a pessimistic / optimistic band), so you
see realistic expectations, not fantasy.

    python dca_plan.py --monthly 100 --years 15

A projection, not a promise. Markets vary widely year to year. The CAPE
signal is for ~10-year horizons. Not investment advice.
"""

import argparse
import os as _os

import numpy as np
import pandas as pd

from markov.valuation import valuation_label, percentile_rank, implied_forward_return
from markov.dca import project_dca


def _DATA(name):
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", name)

H = 120  # 10y window for the CAPE->return fit


def cape_implied(data):
    df = pd.read_csv(data)
    df = df[(df["SP500"] > 0) & (df["PE10"] > 0)].reset_index(drop=True)
    cape = df["PE10"].to_numpy(); sp = df["SP500"].to_numpy()
    fwd = np.full(len(df), np.nan)
    for i in range(len(df) - H):
        fwd[i] = (sp[i + H] / sp[i]) ** (12 / H) - 1
    ok = ~np.isnan(fwd)
    cur = float(cape[-1])
    return (cur, valuation_label(cur), percentile_rank(cur, cape),
            implied_forward_return(cur, cape[ok], fwd[ok]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monthly", type=float, required=True, help="EUR per month")
    ap.add_argument("--years", type=float, required=True)
    ap.add_argument("--data", default=_DATA("sp500_monthly.csv"))
    args = ap.parse_args()

    cur, label, pct, implied = cape_implied(args.data)
    print(f"CAPE now: {cur:.1f} ({label}, more expensive than {pct:.0f}% of history)")
    print(f"CAPE-implied 10y return (price-only): {implied*100:+.1f}%/yr")
    print(f"(add ~2% for dividends -> ~{(implied+0.02)*100:.1f}%/yr total)\n")

    print(f"Plan: {args.monthly:.0f}/month for {args.years:.0f} years\n")
    print(f"  {'scenario':<26}{'return/yr':>10}{'invested':>12}{'value':>14}{'profit':>14}")
    base = implied + 0.02  # include dividends for a total-return estimate
    for name, r in [("pessimistic (CAPE-3%)", base - 0.03),
                    ("CAPE-implied", base),
                    ("optimistic (CAPE+3%)", base + 0.03),
                    ("long-run avg (~7%)", 0.07)]:
        p = project_dca(args.monthly, args.years, max(r, 0))
        print(f"  {name:<26}{r*100:>9.1f}%{p['invested']:>11,.0f}"
              f"{p['final_value']:>14,.0f}{p['profit']:>14,.0f}")

    print("\n  Note: market is expensive now, so near-term expectations should be"
          "\n  modest. DCA buys more units when it falls -- keep going through dips."
          "\n  A projection, not a promise. NOT investment advice.")


if __name__ == "__main__":
    main()
