# Starter kit — quant research engine (reusable for a new strategy)

This repo's reusable core, packaged for lifting into a fresh strategy repo.
Everything is TDD (190 tests), no-look-ahead by construction. Copy `markov/`
and `tests/` as-is; they are dependency-closed and pure-Python + numpy/pandas.

## The methodology (the most valuable thing — reuse this, not just the code)

1. **TDD every signal/feature** (red→green→refactor). No exceptions.
2. **No look-ahead**: every decision at day t uses data ≤ t. Walk-forward.
3. **Sub-period consistency > a single OOS number.** A good OOS Sharpe that
   is negative in any third is regime-luck — reject it (we rejected
   PreHoliday, HS-weekday, crypto-momentum, gate200 on this rule).
4. **Costs are decisive.** Model cost × turnover; high-turnover edges die.
   See `feasibility.py` — at retail costs/sizes, frequent trading loses.
5. **Combine many small, INDEPENDENT, OOS-validated edges** at equal risk
   (`portfolio.combine_alphas`); prove independence with
   `portfolio.orthogonalize`. You can't dilute a loser into a winner.
6. **Single-asset prediction barely beats 50%** (oil hit-rate ~51-53%).
   Edge lives cross-sectionally (rank within a universe) or in diversified
   buy & hold (`dca.py`), not in calling one chart's direction.

## Reusable infrastructure (method-agnostic — keep all)

| Module | Purpose |
|---|---|
| `data.py` | load price CSVs (configurable date/price cols) |
| `data_providers.py` | pluggable data: CSV + live Stooq/Yahoo/CoinMetrics (GitHub raw) |
| `universes.py` | resolve named/list/file universes (TECH, CRYPTO, SP500) |
| `backtest.py` | walk-forward single-asset backtest with costs |
| `signal_portfolio.py` | combined cross-sectional signal → dollar-neutral portfolio |
| `voltarget.py` | volatility targeting (the one robust risk tool) |
| `regime.py` | market-trend on/off gate (no look-ahead) |
| `significance.py` | permutation test for signal significance |
| `portfolio.py` | `combine_alphas` (equal-risk blend), `orthogonalize` (independence) |
| `feasibility.py` | cost/edge/capital reality check |
| `lln.py` | law of large numbers (edge × independent repetition) |
| `dca.py` | dollar-cost-averaging buy & hold simulator |

## Value investing toolkit (the one validated direction)

| Module | Purpose |
|---|---|
| `valuation.py` | CAPE label / percentile / implied 10y return (index-level, validated) |
| `fundamentals.py` | per-stock valuation context vs sector & market |
| `fundamentals_provider.py` | pluggable fundamentals: CSV (now) / FMP live (new repo, needs key) |
| `screener.py` | value+quality scoring & quadrant (separates value from value traps) |

Entrypoints: `valuation_dashboard.py` (CAPE thermometer), `stock_valuation.py`
(per-ticker card), `screener_cli.py` (CHEAP+QUALITY screen). Evidence:
`results/value_investing.md` (CAPE->return validated; CAPE timing fails;
per-stock value is context not a signal -> combine with quality).
Needs a fundamentals data source for live use (snapshot bundled here).

## Signal + UI framework

| Module | Purpose |
|---|---|
| `signal_engine.py` | `Signal` (position→BUY/SELL/HOLD + confidence + breakdown) |
| `engine.py` | `SignalEngine` hybrid: 1 series→time-series, panel→cross-sectional |
| `ts_signals.py` | single-asset latest-position signals (momentum/reversal/volmgd/TOM) |
| `xs_signals.py` | cross-sectional latest-position (rank in universe) |
| `trades.py` | discrete SL/TP trade simulator (visualisation overlay) |
| `svg_chart.py` | zero-dep SVG price chart with trade markers |
| `dashboard.py` | rank + render text/HTML dashboards |

## Factor building blocks (validation status on this data)

| Module | Status on tested data |
|---|---|
| `reversal.py` (Rev10/Rev3) | ✅ market-neutral edge OOS on S&P 500 equities |
| `amihud.py` (illiquidity) | ✅ independent edge (decays late) |
| `resmom.py` (residual momentum) | ✅ most sub-period-consistent edge |
| `seasonality.py` (turn-of-month) | ✅ calendar timing edge |
| `volmanaged.py` (Moreira-Muir) | ✅ market-timing (beta) edge |
| `momentum.py`, `lowvol.py`, `reversal_ensemble.py`, `combined.py` | ⚠️ failed/weak — keep as references |
| `states.py`, `transition.py`, `strategy.py`, `signal.py`, `hmm.py`, `hmm_walkforward.py` | ❌ Markov/HMM — failed OOS; reference only |

## Runnable entrypoints
- `run_portfolio.py` — 6-edge portfolio OOS report
- `validate_engine.py` / `validate_crypto.py` — portfolio-level validation
- `signal_cli.py` / `dashboard.py` / `chart_cli.py` — signals & charts

## Findings archive (read before starting the new method)
`results/REPORT.md` (full narrative), `results/crypto_validation.md`,
`results/oos_hmm_btc.md`, `results/equal_risk_btc.md`.

## How to start the new strategy
1. Copy `markov/` + `tests/` into the new repo; `pip install numpy pandas`.
2. `python -m pytest -q` should pass (190 tests).
3. Build the new signal as a `markov/<name>.py` factor (TDD), expose a
   `latest_position` for the engine, validate via `signal_portfolio` +
   sub-period analysis before trusting it.
4. Keep the discipline above. Not investment advice.
