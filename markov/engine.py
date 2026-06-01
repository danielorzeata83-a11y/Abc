"""SignalEngine: the universal, hybrid buy/sell signal orchestrator.

Auto-detects the mode from the input shape:
  - a single price series -> TIME-SERIES mode (own-price edges; low
    confidence, since single-asset timing is weak -- see results/REPORT.md)
  - a price panel + target -> CROSS-SECTIONAL mode (the target's standing in
    the universe across reversal / illiquidity / residual-momentum alphas)

Edge contributions are combined by equal weight into a target position in
[-1, 1], then turned into a BUY/SELL/HOLD Signal with confidence and a
per-edge breakdown. No look-ahead: every edge uses data up to the last bar.
"""

import numpy as np

from markov.signal_engine import Signal
from markov import ts_signals as ts
from markov import xs_signals as xs


class SignalEngine:
    def __init__(self, threshold=0.15):
        self.threshold = threshold

    def generate(self, prices, dates=None, target_idx=None, volume=None,
                 ticker="", asof=""):
        prices = np.asarray(prices, dtype=float)
        if asof == "" and dates is not None and len(dates):
            asof = str(np.asarray(dates)[-1])[:10]

        if prices.ndim == 1:
            breakdown = self._time_series(prices, dates)
            mode = "time-series"
        elif prices.ndim == 2:
            if target_idx is None:
                raise ValueError("cross-sectional mode requires target_idx")
            breakdown = self._cross_sectional(prices, target_idx, volume)
            mode = "cross-sectional"
        else:
            raise ValueError("prices must be 1-D (series) or 2-D (panel)")

        vals = [v for v in breakdown.values() if v is not None]
        position = float(np.mean(vals)) if vals else 0.0
        return Signal.from_position(
            position, breakdown={k: v for k, v in breakdown.items()
                                 if v is not None},
            mode=mode, threshold=self.threshold, ticker=ticker, asof=asof,
        )

    def _time_series(self, prices, dates):
        b = {
            "ts_momentum": ts.ts_momentum_position(prices),
            "ts_reversal": ts.ts_reversal_position(prices),
            "volmanaged": ts.volmanaged_position(prices),
        }
        if dates is not None and len(dates) == len(prices):
            b["turn_of_month"] = ts.turn_of_month_position(dates)
        return b

    def _cross_sectional(self, prices, target_idx, volume):
        b = {
            "reversal": xs.reversal_position(prices, target_idx, lookback=10),
            "resmom": xs.resmom_position(prices, target_idx) if
            prices.shape[0] > 148 else None,
        }
        if volume is not None:
            b["amihud"] = xs.amihud_position(prices, np.asarray(volume,
                                                                dtype=float),
                                             target_idx)
        return b
