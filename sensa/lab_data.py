"""Price data for the portfolio lab: adjusted closes aligned on common dates, a manifest with a content hash,
and simple daily returns. Problems are reported (dropped tickers, flagged jumps), never silently repaired."""

import hashlib

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable


def load_prices(tickers, history_fn, min_rows=500):
    """history_fn(ticker) -> [(YYYY-MM-DD, adjusted_close)]. Returns (DataFrame on common dates, manifest)."""
    cols, dropped = {}, []
    for t in dict.fromkeys(x.upper() for x in tickers):
        try:
            rows = history_fn(t)
        except (DataUnavailable, ValueError) as e:
            dropped.append({"ticker": t, "reason": str(e)[:100]})
            continue
        if len(rows) < min_rows:
            dropped.append({"ticker": t, "reason": f"only {len(rows)} daily rows (need {min_rows})"})
            continue
        cols[t] = pd.Series([float(c) for _, c in rows], index=[d for d, _ in rows])
    if len(cols) < 2:
        raise DataUnavailable("need at least two tickers with enough history; dropped: " +
                              "; ".join(f"{d['ticker']} ({d['reason']})" for d in dropped))
    prices = pd.DataFrame(cols).dropna().sort_index()
    if len(prices) < min_rows:
        raise DataUnavailable(f"only {len(prices)} common trading days across the tickers (need {min_rows})")
    digest = hashlib.sha256(prices.round(6).to_csv().encode()).hexdigest()
    return prices, {"source": "Yahoo Finance daily adjusted close (dividends and splits)", "tickers": list(prices.columns),
                    "rows": len(prices), "start": prices.index[0], "end": prices.index[-1], "dropped": dropped, "sha256": digest}


def to_returns(prices, jump=0.4):
    r = prices.pct_change().dropna()
    flagged = [{"ticker": c, "date": d, "return": float(r.at[d, c])} for c in r.columns for d in r.index[np.abs(r[c]) > jump]]
    return r, flagged
