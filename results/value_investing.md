# "Invest Like Buffett" — the ONE image whose core claim passes the test

Unlike the trading methods (all ~51% coin-flip on direction), value
investing's central claim is data-backed. Using Shiller CAPE (PE10) on
S&P 500 monthly ~1881-2016, forward 10-year annualised return by valuation:

| regime | CAPE | fwd 10y return/yr | months |
|---|---|---|---|
| CHEAP (be greedy) | <13 | +7.4% | 526 |
| mid | 13-18 | +4.1% | 525 |
| EXPENSIVE (be fearful) | >18 | +3.4% | 542 |

Cheapest decile (CAPE<9): +7.8%/yr; most expensive (CAPE>24): +2.1%/yr.
Correlation CAPE vs forward 10y return: -0.34.

## Verdict: real, but read the fine print
"Be greedy when others are fearful (cheap) / fearful when greedy
(expensive)" is borne out: buying cheap ~doubled forward returns vs buying
expensive, robustly over 135 years. This is the opposite of the trading
charts -- a genuine, evidence-based principle.

Caveats (honesty):
- It works on a 10-YEAR horizon, not for trading. CAPE is useless for
  timing months/years -- markets stay expensive for a decade (1990s, 2010s).
- Per-STOCK intrinsic value is far harder than index CAPE; the smooth
  "intrinsic value" line in the diagram is a cartoon. Estimating one
  company's value well is what Buffett spends his life on -- "anyone can"
  oversells the stock-picking part.
- Buffett's own advice for normal people: buy a low-cost S&P 500 index fund
  and hold (he won a $1M bet that an index beats hedge funds; willed 90% of
  his estate to an index fund). That equals this project's DCA finding.
- The BEHAVIOURAL core (buy cheap, hold, don't panic-sell, don't chase
  hype) is free and anyone CAN do it -- via index + DCA, which automatically
  buys more in crashes (when CAPE falls -> higher forward returns).

This image aligns with the only thing that beat everything else in the
project: diversified, low-cost, long-horizon buy & hold with behavioural
discipline. NOT investment advice.

---

## Can CAPE be used as a trading signal ("green=buy, red=cash")? No.

In/out market timing by CAPE vs buy & hold (S&P 500 monthly 1881-2023, price):

| strategy | x money | CAGR | MaxDD | Sharpe | % invested |
|---|---|---|---|---|---|
| Buy & Hold | 730x | 4.7% | -85% | 0.40 | 100% |
| CAPE<15 in/out | 35x | 2.5% | -60% | 0.29 | 40% |
| CAPE<20 in/out | 71x | 3.0% | -73% | 0.30 | 70% |
| CAPE<25 in/out | 268x | 4.0% | -80% | 0.36 | 86% |
| CAPE-scaled (0-100%) | 340x | 4.2% | -80% | 0.38 | 88% |

Every timing variant UNDERPERFORMS buy & hold on return AND Sharpe (and
cash misses dividends, so real-world timing is even worse).

### Why a PREDICTIVE signal still fails as a TRADING signal
CAPE predicts 10y returns (corr -0.34) but "expensive" means lower-but-still
-POSITIVE expected return, not negative. Going to cash forfeits that positive
return; the market's positive drift is very hard to beat by switching in/out.
For timing to pay, the signal would need to predict NEGATIVE returns -- it
doesn't. The market also stayed "expensive" for decades post-1990, so a fixed
threshold sits out huge gains.

### The correct use: a gentle TILT, not an on/off switch
Stay invested always, but allocate more when cheap and less when expensive
(the CAPE-scaled variant ~matches buy&hold risk-adjusted with lower average
exposure). That is exactly what monthly DCA does automatically. Tilt = fine;
in/out timing = worse. The deepest lesson: even a genuinely predictive signal
does not make a good market-timing trade. NOT investment advice.
