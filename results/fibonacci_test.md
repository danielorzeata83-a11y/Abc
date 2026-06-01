# Testing the "Fibonacci Secrets" claim — it's risk/reward, not magic numbers

Mechanical test on 8 assets (BTC, WTI, Brent, 8 S&P stocks): detect swings
(zig-zag, 8% threshold), and for each leg simulate entering at each
retracement level with target = the prior swing, stop = the opposite
extreme. Close-only, no costs, no OOS (indicative).

## Expectancy in R per Fibonacci level
| level | win rate | RR | exp(R) | n |
|---|---|---|---|---|
| 38.2% | 37% | 0.62 | -0.40 | 1235 |
| 50.0% | 33% | 1.00 | -0.34 | 1134 |
| 61.8% | 28% | 1.62 | -0.27 | 1007 |
| 78.6% | 20% | 3.67 | -0.07 | 767 |
| 88.6% | 13% | 7.77 | +0.18 | 521 |

Win rate DECREASES with depth (opposite of the image's "probability"
labels); expectancy increases only because reward/risk grows as the stop
tightens near the extreme.

## Is anything special about Fibonacci levels? (fine grid)
| level | exp(R) | Fib? |
|---|---|---|
| 30.0% | -0.44 | |
| 38.2% | -0.40 | FIB |
| 45.0% | -0.36 | |
| 50.0% | -0.34 | FIB |
| 61.8% | -0.27 | FIB |
| 70.0% | -0.24 | |
| 78.6% | -0.07 | FIB |
| 85.0% | +0.04 | |
| 88.6% | +0.18 | FIB |
| 95.0% | +1.15 | |

The expectancy curve is SMOOTH in depth; non-Fib levels (85%, 95%) lie on
the same curve, and 95% (not a Fibonacci number) is the best of all. There
is nothing special about 38.2/61.8/78.6/88.6.

## Verdict
The image's "deeper = better" is directionally true in EXPECTANCY, but the
driver is risk/reward geometry (deep entry + tight stop at the extreme +
full-swing target), NOT Fibonacci. Any level works; deeper = better RR.
"Fibonacci Secrets" is marketing dressing on a pure RR effect -- the same
lesson as 1:2 RR: edge comes from asymmetry, not prediction.

Caveats (why this is NOT a green light): tiny win rates at the good levels
(13% at 88.6%, lower at 95%) are psychologically brutal; close-only data
makes tight deep stops look better than reality (intrabar wicks would hit
them more); no costs, no OOS, small samples at the extremes. NOT
investment advice.
