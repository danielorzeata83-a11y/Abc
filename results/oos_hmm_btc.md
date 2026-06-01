# Out-of-sample walk-forward HMM on BTC

Run: refit_every=90, warmup=250, seed=42, Coin Metrics BTC 2010-2026.

```
OOS HMM positions: 5538  (computed in 81s)
Mean pos: -0.433  (short 95% of the time, long 5%, flat 0%)

Permutation significance (one-sided):
  observed   = -0.000142
  null_mean  = -0.001320
  p_value    =  0.0005   (SIGNIFICANT, but observed is NEGATIVE)

Net return  0 bps: -95%
Net return 10 bps: -98%
Buy & Hold same window: +8,669,561%
```

## Interpretation

The walk-forward HMM (no look-ahead) went short ~95% of the time on an
asset that rose ~86,000x, losing 95-98% of capital. The "significant"
p-value only means it shorted slightly less badly than random shorting --
statistical signal without profitability.

The gap between in-sample HMM (apparent positive timing, p=0.0005) and
out-of-sample HMM (-95%) is direct empirical evidence of OVERFITTING via
HMM label instability / label-switching. This is the central cautionary
finding of the project: a method that looks brilliant in-sample can be
ruinous once future data is properly excluded.
