# Plan: universal SignalEngine (buy/sell signals)

Goal: load a chart (e.g. NVDA) and emit a buy/sell signal. Hybrid:
- 1 price series in  -> TIME-SERIES mode (own-price edges, low confidence)
- a panel + target   -> CROSS-SECTIONAL mode (target's position in universe)

Output (decided): continuous `position in [-1, 1]` + label BUY/SELL/HOLD on
thresholds + `confidence`, plus a per-edge breakdown and a disclaimer.

## Edges reused (already built + OOS-validated; see results/REPORT.md)
- Time-series: VolManaged, TurnOfMonth, + TS-momentum (price vs MA),
  TS-reversal (z-score of recent return).
- Cross-sectional: Rev10, Rev3, Amihud, ResidualMomentum (+ TOM/VolManaged
  on the universe market).

## Core refactor
Each edge currently returns a RETURN STREAM (for backtesting). Add a
`latest_position(...)` / `latest_weights(...)` that returns today's target
position using data up to the last bar only (no look-ahead).

## Phases (all TDD)
1. `Signal` dataclass + position->label/confidence mapping. (markov/signal_engine.py)
2. Time-series adapters: latest_position for VolManaged, TOM, TS-momentum,
   TS-reversal.
3. Cross-sectional adapters: latest target position for Rev10/Rev3/Amihud/ResMom.
4. `SignalEngine.generate(prices, dates, target=None, universe=None)` —
   auto-detect mode, run edges, equal-risk combine (weights from history),
   emit Signal with breakdown.
5. CLI `signal_cli.py --ticker NVDA --universe sp500` (NVDA is in data/sp500.csv).
6. Honesty harness: historical OOS Sharpe of the engine's NVDA signal.

## Honest constraints
- Network limited to allowlisted CSV sources; data loader is pluggable
  (CSV today, live API when allowed). NVDA demo uses data/sp500.csv (2013-18).
- Single-asset mode is weak (proven in this project) -> flagged low-confidence.
- Not investment advice.
