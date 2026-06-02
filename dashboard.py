"""Signal dashboard: buy/sell signals for a whole universe at once.

Loads a data provider, resolves a universe, runs the cross-sectional
SignalEngine for every ticker, then prints a ranked table and writes an
HTML dashboard.

Examples:
    python dashboard.py --provider csv:data/sp500.csv --universe TECH
    python dashboard.py --provider csv:data/sp500.csv --universe SP500 --top 15
    python dashboard.py --provider csv:data/sp500.csv --universe AAPL,NVDA,MSFT

Live providers (when the host is allowlisted):
    python dashboard.py --provider stooq --universe AAPL,NVDA,MSFT

Nothing here is investment advice.
"""

import argparse
import os as _os
def _DATA(name):
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", name)

from markov.data_providers import get_provider, DataUnavailable, CSVPanelProvider
from markov.universes import resolve_universe, candidate_tickers
from markov.engine import SignalEngine
from markov.dashboard import render_table, render_html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="csv:"+_DATA("sp500.csv"))
    ap.add_argument("--universe", default="TECH")
    ap.add_argument("--top", type=int, default=None,
                    help="show only the strongest N buys and N sells")
    ap.add_argument("--html", default="results/dashboard.html")
    ap.add_argument("--threshold", type=float, default=0.15)
    args = ap.parse_args()

    provider = get_provider(args.provider)
    is_csv = isinstance(provider, CSVPanelProvider)
    try:
        if is_csv:
            panel = provider.fetch(None)            # CSV can enumerate all
        else:
            cands = candidate_tickers(args.universe)  # live needs explicit list
            if cands is None:
                raise SystemExit(f"universe {args.universe!r} can't be "
                                 f"enumerated on a live provider; pass a "
                                 f"named universe or ticker list")
            panel = provider.fetch(cands)
    except DataUnavailable as exc:
        raise SystemExit(str(exc))

    universe = resolve_universe(args.universe, panel.tickers)
    engine = SignalEngine(threshold=args.threshold)
    asof = str(panel.dates[-1])[:10]

    signals = []
    for tic in universe:
        idx = panel.tickers.index(tic)
        signals.append(engine.generate(
            panel.prices, dates=panel.dates, target_idx=idx,
            volume=panel.volume, ticker=tic, asof=asof,
        ))

    title = f"{args.universe} signals - {asof}"
    print(title)
    if not args.provider.startswith("csv:"):
        print("WARNING: cross-sectional edges are OOS-validated on EQUITIES "
              "only; on crypto they backtest negative (see "
              "results/crypto_validation.md). Treat as UNVALIDATED.")
    print(render_table(signals, top_n=args.top))

    import os as __os
    __os.makedirs(__os.path.dirname(__os.path.abspath(args.html)), exist_ok=True)
    with open(args.html, "w") as fh:
        fh.write(render_html(signals, title=title, top_n=args.top))
    print(f"\nHTML dashboard written to {args.html}")


if __name__ == "__main__":
    main()
