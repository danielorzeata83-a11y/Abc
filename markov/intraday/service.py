"""Pure read+compute service layer for intraday data.

Turns cached 15-minute bars into chart candles and a features dict.
No network calls; raises DataUnavailable when the cache is absent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.bars import resample
from markov.intraday.cache import read_bars
from markov.intraday import indicators as ind

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIMEFRAMES = ("15m", "30m", "1h", "4h", "1day")

# Default data directory: <repo>/data/intraday (relative to this file's location)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATA_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "data", "intraday"))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class Config:
    watchlist: tuple = ("NVDA", "AAPL", "MSFT", "AMD", "TSLA")
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: str = _DEFAULT_DATA_DIR
    refresh_interval_min: int = 30
    backfill_months: int = 12

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Config":
        """Build Config from an env dict (or os.environ if None).

        Tolerant: invalid/missing values fall back to defaults.
        """
        if env is None:
            env = dict(os.environ)

        defaults = cls()

        # INTRADAY_WATCHLIST — comma-separated symbols, uppercased, stripped
        raw_wl = env.get("INTRADAY_WATCHLIST", "")
        if raw_wl.strip():
            watchlist = tuple(s.strip().upper() for s in raw_wl.split(",") if s.strip())
        else:
            watchlist = defaults.watchlist

        # INTRADAY_PORT — integer
        raw_port = env.get("INTRADAY_PORT", "")
        try:
            port = int(raw_port)
        except (ValueError, TypeError):
            port = defaults.port

        # INTRADAY_DATA_DIR — raw string
        data_dir = env.get("INTRADAY_DATA_DIR", defaults.data_dir) or defaults.data_dir

        return cls(
            watchlist=watchlist,
            host=defaults.host,
            port=port,
            data_dir=data_dir,
            refresh_interval_min=defaults.refresh_interval_min,
            backfill_months=defaults.backfill_months,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_finite(arr: np.ndarray) -> float | None:
    """Return the last finite value in arr, or None if none exist."""
    arr = np.asarray(arr, dtype=float)
    finite = arr[np.isfinite(arr)]
    if len(finite) == 0:
        return None
    return float(finite[-1])


def _epoch_seconds(ts) -> int:
    """Convert a pandas Timestamp (or datetime64) to Unix epoch seconds."""
    return int(pd.Timestamp(ts).value // 1_000_000_000)


# ---------------------------------------------------------------------------
# get_candles
# ---------------------------------------------------------------------------

def get_candles(symbol: str, tf: str, data_dir: str) -> list[dict]:
    """Return OHLCV+vwap candles for *symbol* at timeframe *tf*.

    Reads the 15m cache, resamples to *tf*, and returns one dict per bar.

    Keys:
      time  — int epoch seconds (intraday tf) or "YYYY-MM-DD" string (1day)
      open, high, low, close, volume — float
      vwap  — float session-anchored VWAP (only for intraday tfs; omitted when NaN)

    Raises DataUnavailable if the cache file is absent.
    """
    bars = read_bars(data_dir, symbol)
    if bars is None:
        raise DataUnavailable(f"No cached data for {symbol} in {data_dir}")

    resampled = resample(bars, tf)
    df = resampled.to_frame()

    is_intraday = tf != "1day"

    if is_intraday:
        # Session-anchored cumulative VWAP, reset per calendar day.
        # typical price = (H+L+C)/3; VWAP = cumsum(tp*vol) / cumsum(vol) per day
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        tpv = tp * df["volume"]
        date_group = df.index.normalize()
        cum_tpv = tpv.groupby(date_group).cumsum()
        cum_vol = df["volume"].groupby(date_group).cumsum()
        vwap_series = cum_tpv / cum_vol

    result = []
    for ts, row in df.iterrows():
        if is_intraday:
            time_val = _epoch_seconds(ts)
        else:
            time_val = str(ts.date())

        candle: dict = {
            "time": time_val,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }

        if is_intraday:
            v = vwap_series.loc[ts]
            if np.isfinite(v):
                candle["vwap"] = float(v)

        result.append(candle)

    return result


# ---------------------------------------------------------------------------
# get_features
# ---------------------------------------------------------------------------

def get_features(symbol: str, tf: str, data_dir: str, window: int = 50) -> dict:
    """Compute TIER-1 indicator features for *symbol* at timeframe *tf*.

    Returns a dict with exactly these keys:
      garman_klass, rogers_satchell, realized_variance, bipower_variation,
      jump, jump_ratio, hurst, fdi, permutation_entropy, rqa_determinism,
      corwin_schultz, roll_measure, high_52w_proximity, max_effect

    Each value is a float (latest finite value) or None (not enough data).

    Raises DataUnavailable if the cache file is absent.
    """
    bars = read_bars(data_dir, symbol)
    if bars is None:
        raise DataUnavailable(f"No cached data for {symbol} in {data_dir}")

    resampled = resample(bars, tf)
    n = len(resampled)

    o = resampled.open
    h = resampled.high
    l = resampled.low
    c = resampled.close

    # Adaptive window: min(window, n-1) so we always have at least 1 step
    w = min(window, max(n - 1, 1))

    # --- Volatility ---
    gk = ind.garman_klass(o, h, l, c, w)
    rs = ind.rogers_satchell(o, h, l, c, w)
    rv = ind.realized_variance(c, w)
    bv = ind.bipower_variation(c, w)
    jump_arr, jump_ratio_arr = ind.jump_component(c, w)

    # --- Complexity ---
    hurst_arr = ind.hurst(c, w)
    fdi_arr = ind.fdi(c, w)

    # permutation entropy: m=3 is standard; window same as w
    pe_arr = ind.permutation_entropy(c, m=3, window=w)

    # rqa: cap window at 200; eps = 0.2 * std of recent window, guarded > 0
    rqa_w = min(w, 200)
    recent = c[-rqa_w:] if n >= rqa_w else c
    std_recent = float(np.std(recent))
    eps = 0.2 * std_recent if std_recent > 0 else 1e-6
    rqa_arr = ind.rqa_determinism(c, rqa_w, eps)

    # --- Liquidity ---
    cs_arr = ind.corwin_schultz(h, l)
    roll_arr = ind.roll_measure(c, w)

    # --- Behavioral ---
    lookback_52w = min(n, 252)
    prox_arr = ind.high_52w_proximity(c, lookback_52w)

    # max_effect: bar returns; window min(21, n-1)
    bar_returns = np.diff(c) / np.where(c[:-1] != 0, c[:-1], 1.0)
    me_w = min(21, max(len(bar_returns) - 1, 1))
    me_arr = ind.max_effect(bar_returns, me_w)

    return {
        "garman_klass": _last_finite(gk),
        "rogers_satchell": _last_finite(rs),
        "realized_variance": _last_finite(rv),
        "bipower_variation": _last_finite(bv),
        "jump": _last_finite(jump_arr),
        "jump_ratio": _last_finite(jump_ratio_arr),
        "hurst": _last_finite(hurst_arr),
        "fdi": _last_finite(fdi_arr),
        "permutation_entropy": _last_finite(pe_arr),
        "rqa_determinism": _last_finite(rqa_arr),
        "corwin_schultz": _last_finite(cs_arr),
        "roll_measure": _last_finite(roll_arr),
        "high_52w_proximity": _last_finite(prox_arr),
        "max_effect": _last_finite(me_arr),
    }
