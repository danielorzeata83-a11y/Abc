"""Pluggable data-provider layer.

A provider turns a list of tickers into a PanelData(prices, volume, dates,
tickers). The CSV provider reads the bundled long-format file and works
offline. Live providers (Stooq, Yahoo) are implemented against their HTTP
CSV/JSON endpoints but only succeed when the host is allowlisted; offline
they raise DataUnavailable with a clear message.

    get_provider("csv:data/sp500.csv")  -> CSVPanelProvider
    get_provider("stooq")               -> StooqProvider
    get_provider("yahoo")               -> YahooProvider
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


class DataUnavailable(RuntimeError):
    """Raised when a live source can't be reached (e.g. host not allowlisted)."""


@dataclass
class PanelData:
    prices: np.ndarray   # (T, N) close
    volume: np.ndarray   # (T, N)
    dates: np.ndarray    # (T,)
    tickers: list


class CSVPanelProvider:
    """Reads a long-format CSV (date, open, high, low, close, volume, Name)."""

    def __init__(self, path):
        self.path = path

    def fetch(self, tickers=None):
        raw = pd.read_csv(self.path)
        close = raw.pivot(index="date", columns="Name", values="close").sort_index()
        vol = raw.pivot(index="date", columns="Name", values="volume").sort_index()
        close = close.dropna(axis=1)
        if tickers is None:
            tickers = list(close.columns)
        else:
            missing = [t for t in tickers if t not in close.columns]
            if missing:
                raise KeyError(f"tickers not in panel: {missing}")
        close = close[tickers]
        vol = vol[tickers]
        return PanelData(
            prices=close.to_numpy(),
            volume=vol.to_numpy().astype(float),
            dates=pd.to_datetime(close.index).to_numpy(),
            tickers=list(tickers),
        )


class _LiveProvider:
    """Base for live HTTP providers; subclasses build per-ticker frames."""

    name = "live"

    def _fetch_one(self, ticker):  # pragma: no cover - network
        raise NotImplementedError

    def fetch(self, tickers):
        if not tickers:
            raise ValueError("live providers require an explicit ticker list")
        frames = {}
        for t in tickers:
            try:
                frames[t] = self._fetch_one(t)
            except DataUnavailable:
                raise
            except Exception as exc:  # network/parse errors -> uniform signal
                raise DataUnavailable(
                    f"{self.name}: could not fetch {t} ({exc}). In this "
                    f"environment only allowlisted hosts are reachable."
                ) from exc
        closes = pd.concat({t: f["close"] for t, f in frames.items()}, axis=1).dropna()
        vols = pd.concat({t: f["volume"] for t, f in frames.items()}, axis=1).reindex(closes.index)
        return PanelData(
            prices=closes.to_numpy(),
            volume=vols.to_numpy().astype(float),
            dates=pd.to_datetime(closes.index).to_numpy(),
            tickers=list(closes.columns),
        )


class StooqProvider(_LiveProvider):
    name = "stooq"

    def _fetch_one(self, ticker):  # pragma: no cover - network
        import urllib.request
        url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
        with urllib.request.urlopen(url, timeout=15) as r:
            df = pd.read_csv(r)
        df = df.rename(columns=str.lower).set_index("date")
        return df[["close", "volume"]]


class YahooProvider(_LiveProvider):
    name = "yahoo"

    def _fetch_one(self, ticker):  # pragma: no cover - network
        import json
        import urllib.request
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?range=2y&interval=1d")
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)
        res = data["chart"]["result"][0]
        ts = pd.to_datetime(res["timestamp"], unit="s")
        q = res["indicators"]["quote"][0]
        return pd.DataFrame({"close": q["close"], "volume": q["volume"]},
                            index=ts)


def get_provider(spec):
    """Resolve a provider spec: 'csv:PATH', 'stooq', or 'yahoo'."""
    if spec.startswith("csv:"):
        return CSVPanelProvider(spec[4:])
    if spec == "stooq":
        return StooqProvider()
    if spec == "yahoo":
        return YahooProvider()
    raise ValueError(f"unknown provider spec: {spec!r}")
