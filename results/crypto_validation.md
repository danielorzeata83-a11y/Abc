# Crypto edge validation — neither reversal nor momentum is robust

Live Coin Metrics data, CRYPTO_WIDE (36 coins with common history),
2020-10 → 2026-03, dollar-neutral combined signal, 2bps, PPY=365.

## Reversal (the equities edge) — fails on crypto
| rev_lb | full | OOS | third1 | third2 | third3 |
|---|---|---|---|---|---|
| 7  | -0.11 | -0.16 | -0.23 | +0.13 | -0.15 |
| 14 | -0.38 | -0.83 | -0.26 | -0.33 | -0.55 |
| 21 | -0.60 | -0.45 | -1.01 | -0.44 | -0.29 |
| 63 | +0.10 | -0.17 | +0.48 | -0.20 | -0.06 |

Reversal is negative almost everywhere. The equities edge does NOT transfer.

## Momentum (the crypto stylized fact) — regime-luck, not robust
| rev_lb | full | OOS | third1 | third2 | third3 |
|---|---|---|---|---|---|
| 7  | -0.67 | +0.56 | -2.17 | -0.49 | +0.74 |
| 14 | -0.18 | +1.22 | -1.61 | +0.18 | +1.10 |
| 21 | -0.11 | +0.80 | -1.05 | +0.03 | +0.79 |
| 63 | -0.73 | +0.66 | -2.63 | -0.09 | +0.72 |

Momentum's strong OOS Sharpe is an ARTIFACT: the OOS window (last 40%)
coincides with a favourable recent regime (third3). The first third
(2020-2022 mania + crash) is strongly NEGATIVE, and full-sample is
negative. It fails the sub-period consistency bar that reversal/Amihud
PASSED on equities (positive in all thirds).

## Verdict
No cross-sectional crypto signal tested here is robust across regimes:
- reversal: consistently negative;
- momentum: positive only in the recent regime (regime-luck), negative in
  2020-2022.

The crypto dashboard is functional but its signals are NOT validated; the
equities edges do not carry to crypto, and a naive flip to momentum only
looks good because of the OOS window placement. A credible crypto strategy
would need regime-aware design and far more history/coins than this sample.
This is the same discipline applied throughout: a good-looking OOS number
that collapses under sub-period analysis is rejected. NOT investment advice.
