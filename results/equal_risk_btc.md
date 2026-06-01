# Equal-risk comparison on BTC (volatility targeting)

Both strategies scaled to 20% annual vol (past-only, no look-ahead),
10 bps cost on leveraged turnover. Coin Metrics BTC 2010-2026.

```
Strategy                NetRet    Sharpe   MaxDD
Buy&Hold (vol-tgt)     19,424%     1.57    -39%
Markov   (vol-tgt)     17,479%     1.48    -41%

reference (no vol-targeting):
  Buy&Hold raw   Sharpe 1.44   MaxDD -93%
  Markov raw     Sharpe 1.31   MaxDD -71%
```

## Interpretation

At equal risk, buy & hold still wins: higher return (19,424% vs 17,479%),
higher Sharpe (1.57 vs 1.48), and -- crucially -- even a SLIGHTLY better
drawdown (-39% vs -41%). The Markov method's only apparent edge in the raw
comparison (a milder -71% vs -93% drawdown) was simply a side effect of
holding less exposure on average, NOT genuine risk-adjusted skill. Once
you give buy & hold the same risk budget, that edge evaporates.

Volatility targeting itself is the real hero here: it cut both strategies'
drawdowns from ~90%/-71% to ~40% while keeping returns. That is a far more
valuable, robust finding than the Markov method.

## Final verdict

On trending crypto (BTC), the Markov "hedge-fund method" is dominated by
plain buy & hold on every axis once risk is equalised. It is a sound
teaching tool, not a live edge.
