# Buy-the-Dip — rezultate (onest)

**Intrebarea care a pornit testul:** „putem fi lacomi, sa cumparam cat e jos?"
(pe RGTI, un titlu speculativ). RGTI nu e in setul nostru (date S&P 2013-18;
RGTI listat 2022), deci am testat IDEEA „cumpara dipul" pe nume cu istoric real.

**Sistem** (mecanic, cauzal, long-only): cumpara cand drawdown <= -`dip` fata de
maximul ultimelor `lookback` zile; vinde cand pretul revine peste o MA scurta.
Pragul `dip` ales prin walk-forward (in-sample), raportat OUT-OF-SAMPLE.
Cost 5 bps. Prefix-stabil (fara look-ahead) -- `tests/test_dipbuy.py`.

## Verdict: NU bate buy-and-hold; pooled NEsemnificativ

| Nume | dip | SISTEM Sh | B&H Sh | edge_Sh | in-mkt | p |
|---|---|---|---|---|---|---|
| MSFT | 0.10 | +1.44 | +1.29 | +0.15 | 10% | 0.006 |
| XOM | 0.10 | +0.38 | +0.05 | +0.34 | 18% | 0.15 |
| NVDA | 0.15 | +0.30 | **+2.33** | **−2.02** | 8% | 0.76 |
| AMZN | 0.15 | +0.32 | +1.61 | −1.29 | 6% | 0.39 |
| (restul) | … | … | … | **negativ** | 5-23% | >0.1 |

```
POOLED (un singur test pe tot watchlist-ul): net=+235%  Sharpe=+0.43  p=0.144
```

**p=0.144 → timing buy-the-dip NEdistins de noroc** la nivel de portofoliu.
MSFT (p=0.006) per-nume e exact false-pozitivul de testare multipla (12 nume):
se spala in agregat.

## Statistica ucigatoare pentru „cumpara cat e jos"

NVDA: buy-the-dip a facut **+5.9%** OOS, stand in piata doar **8%** din timp.
Buy-and-hold pe acelasi NVDA: **+862%**. Asteptand „dipul" ai stat in cash si ai
ratat fix marele trend. Pe nume care urca, „cumpara cand e jos" te tine pe
margine cat castiga ceilalti.

## Concluzie (raspuns la intrebare)

Testat onest, „cumpara cat e jos":
- nu adauga edge de timing semnificativ (pooled p=0.144),
- subperformeaza buy-and-hold pe risc ajustat pe majoritatea numelor,
- te tine in cash si rateaza trendurile mari.

Asta nu spune ce va face RGTI. Spune ca *regula generala* „cumpar fiindca e jos"
nu are suport pe date -- e o narativa, nu un edge. Pe un titlu speculativ singular,
fara reper fundamental, e si mai riscant. NU este consiliere de investitii.
