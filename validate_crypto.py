"""Validate the cross-sectional edges OOS on the live crypto panel.

Same rigorous process used on equities (see validate_engine.py and
results/REPORT.md), now on Coin Metrics crypto data: build the combined
signal as a dollar-neutral portfolio, report full-sample and out-of-sample
Sharpe plus per-third sub-period consistency. Crypto trades every day so
annualisation uses 365.

This tests whether the edges -- validated on stocks -- transfer to crypto,
or whether the crypto dashboard is just unvalidated extrapolation.
Nothing here is investment advice.
"""

import numpy as np

from markov.data_providers import get_provider, DataUnavailable
from markov.universes import candidate_tickers
from markov.signal_portfolio import signal_portfolio_returns

PPY = 365


def _sharpe(d):
    v = d.std() * np.sqrt(PPY)
    return (d.mean() * PPY) / v if v > 0 else 0.0


def main():
    tickers = candidate_tickers("CRYPTO")
    try:
        panel = get_provider("coinmetrics").fetch(tickers)
    except DataUnavailable as exc:
        raise SystemExit(str(exc))

    P, V = panel.prices, panel.volume
    asof = str(panel.dates[-1])[:10]
    start = str(panel.dates[0])[:10]
    # Crypto volume history is patchy; only use it if mostly present.
    use_vol = np.isfinite(V).mean() > 0.5
    daily = signal_portfolio_returns(P, V if use_vol else None,
                                     rev_lb=10, holding=5, cost=2e-4)
    split = int(len(daily) * 0.6)

    print(f"Crypto edge validation - {len(panel.tickers)} coins, "
          f"{start} -> {asof}  ({P.shape[0]} days)")
    print(f"  volume usable: {use_vol}  (amihud {'on' if use_vol else 'OFF'})")
    print(f"  full-sample Sharpe : {_sharpe(daily):+.2f}")
    print(f"  out-of-sample Sharpe: {_sharpe(daily[split:]):+.2f}")
    n = len(daily)
    for i, (a, b) in enumerate([(0, n // 3), (n // 3, 2 * n // 3),
                                (2 * n // 3, n)]):
        print(f"    third {i + 1}: Sharpe {_sharpe(daily[a:b]):+.2f}")
    eq = np.cumprod(1 + daily[split:])
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    print(f"  OOS MaxDD {dd*100:.0f}%")
    print("\n  NOTE: small universe + patchy data -> treat as indicative only.")
    print("  Research artifact - not investment advice.")


if __name__ == "__main__":
    main()
