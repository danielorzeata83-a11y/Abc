# Testing classic indicators (RSI/MACD/Stochastic) — they don't beat a coin flip

Mechanical test on 8 assets (BTC, WTI, Brent, 5 S&P stocks): does each
indicator's standard signal predict the sign of the next 5-day move?

| indicator | hit rate | signals |
|---|---|---|
| RSI(30/70) | 46.1% | 3932 |
| MACD cross | 50.1% | 2475 |
| Stochastic(20/80) | 48.7% | 19575 |

(50% = coin flip; need >~52-53% to beat costs.)

## Findings
- None beats a coin flip. RSI and Stochastic are BELOW 50% -- the
  "oversold = buy" logic catches falling knives in downtrends.
- These are lagging math functions of past price; they hold no information
  beyond price, and single-asset price prediction is ~51% (see the oil
  hit-rate test). Repackaging price as RSI/MACD/Stoch adds nothing.
- Stacking ~10 such indicators does not manufacture an edge: combining
  non-predictive signals stays non-predictive (you can't dilute losers
  into winners).

## Why annotated charts look perfect
Buy/Sell arrows are drawn in hindsight on exact tops/bottoms; live (right
edge) you don't know which signal is real. With ~10 indicators, at any turn
SOME indicator fired, so a narrative is retrofit; the whipsaws (false
signals) are not shown.

Caveat: 5-day horizon, simple thresholds; other parameters vary the exact
numbers but the broad result (near or below coin-flip) matches the whole
project and the academic literature. NOT investment advice.
