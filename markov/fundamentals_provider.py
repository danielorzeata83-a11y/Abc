"""Pluggable fundamentals-provider layer (mirrors data_providers.py).

A provider returns a DataFrame of valuation fundamentals (Symbol, Sector,
P/E, P/B, P/S, Market Cap, EBITDA, Dividend Yield) for the screener and the
per-stock valuation card. The CSV provider works now on the bundled
snapshot; the live FMP (Financial Modeling Prep) provider is implemented but
only works with an API key and outbound network (raises DataUnavailable
otherwise). Swap CSV -> fmp in the new repo for live data.

    get_fundamentals_provider("csv:data/sp500_financials.csv")
    get_fundamentals_provider("fmp:<API_KEY>")
"""

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable

FUND_COLUMNS = ("Symbol", "Sector", "Price/Earnings", "Price/Book",
                "Price/Sales", "Market Cap", "EBITDA", "Dividend Yield")


class CSVFundamentalsProvider:
    """Reads a financials snapshot CSV (the bundled S&P 500 file)."""

    def __init__(self, path):
        self.path = path

    def fetch(self, tickers=None):
        df = pd.read_csv(self.path)
        if tickers is not None:
            missing = [t for t in tickers if t not in set(df["Symbol"])]
            if missing:
                raise KeyError(f"tickers not in fundamentals: {missing}")
            df = df[df["Symbol"].isin(tickers)].reset_index(drop=True)
        return df


class FMPProvider:
    """Live fundamentals via Financial Modeling Prep (needs API key + network).

    Maps FMP ratio/profile fields to FUND_COLUMNS. In this sandbox the host
    is not allowlisted, so fetch() raises DataUnavailable; in the new repo
    with a key and open network it returns live data.
    """

    BASE = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key):
        self.api_key = api_key

    def _fetch_one(self, ticker):  # pragma: no cover - network
        import json
        import urllib.request
        def get(path):
            url = f"{self.BASE}/{path}?apikey={self.api_key}"
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.load(r)
        prof = get(f"profile/{ticker}")[0]
        rat = get(f"ratios-ttm/{ticker}")[0]
        km = get(f"key-metrics-ttm/{ticker}")[0]
        return {
            "Symbol": ticker,
            "Sector": prof.get("sector", "Unknown"),
            "Price/Earnings": rat.get("peRatioTTM"),
            "Price/Book": rat.get("priceToBookRatioTTM"),
            "Price/Sales": rat.get("priceToSalesRatioTTM"),
            "Market Cap": prof.get("mktCap"),
            "EBITDA": km.get("enterpriseValueTTM") and km.get("evToOperatingCashFlowTTM"),
            "Dividend Yield": rat.get("dividendYielTTM") or rat.get("dividendYieldTTM"),
        }

    def fetch(self, tickers):
        if not tickers:
            raise ValueError("FMP provider requires an explicit ticker list")
        rows = []
        for t in tickers:
            try:
                rows.append(self._fetch_one(t))
            except Exception as exc:  # noqa: BLE001
                raise DataUnavailable(
                    f"FMP: could not fetch {t} ({exc}). Needs an API key and "
                    f"outbound network (host not allowlisted in this sandbox)."
                ) from exc
        return pd.DataFrame(rows)


def get_fundamentals_provider(spec):
    """Resolve 'csv:PATH' or 'fmp:API_KEY'."""
    if spec.startswith("csv:"):
        return CSVFundamentalsProvider(spec[4:])
    if spec.startswith("fmp:"):
        return FMPProvider(spec[4:])
    raise ValueError(f"unknown fundamentals provider: {spec!r}")
