# Markov Regime Research Engine

A **research engine** for the Markov / hidden-Markov "regime" trading method
(bull / sideways / bear states, transition matrix, multi-step forecasts,
signal generation). Built test-first.

> ⚠️ **This is a research tool, not a money machine.** The underlying method
> (a 3-state, memory-1 Markov chain on daily returns) is a sound *teaching*
> model but is far too simple to be an institutional edge. Expected realistic
> outcome of the raw method, after costs: break-even to slightly negative.
> Nothing here is investment advice. Decisions with real capital, and the
> risk, are entirely the user's.

## Why build it anyway

To do it *honestly*: clean data → reproduce the method → **strict walk-forward
validation** → realistic costs → **statistical significance test**. The point
is to find out whether there is a real edge, and to say so plainly if there
isn't.

## Pipeline

| Step | Module | Status |
|---|---|---|
| 1-2 State classification (±5% / 20-day) | `markov/states.py` | ✅ tested |
| 3 Transition matrix (3×3, rows sum to 1) | `markov/transition.py` | ✅ tested |
| 6-7 Multi-step forecast + stationary dist. | `markov/transition.py` | ✅ tested |
| 5/8 Signal = P(bull) − P(bear) | `markov/signal.py` | ✅ tested |
| 9 Walk-forward backtest (no look-ahead) | _next_ | ⏳ |
| 7-cost Transaction-cost model | _next_ | ⏳ |
| stat Monte-Carlo significance | _next_ | ⏳ |
| 10 Hidden Markov Model (unsupervised states) | _later_ | ⏳ |
| data Real crypto OHLCV loader | _blocked on network_ | ⏳ |

## Known constraints in this environment

- Live crypto exchange APIs (Binance, Coinbase, Kraken, CoinGecko) are
  **blocked by the network policy**. The engine is built and validated on
  synthetic data; real BTC/ETH data plugs into the same loader interface
  once an exchange host is allow-listed.

## Run the tests

```bash
pip install numpy pandas pytest
python3 -m pytest -q
```
