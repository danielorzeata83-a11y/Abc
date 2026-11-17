# Trend-Pullback — rezultate (onest)

**Sistem** (definit impreuna): trend confirmat (`close > MA50` + MA50 in crestere)
→ intrare la retest pe MA50 → iesire chandelier ATR. Long-only. Tot cauzal, fara
repaint (test de prefix-stabilitate in `tests/test_trendpull.py`).

**Validare:** walk-forward single-holdout — multiplicatorul ATR ales pe felia
in-sample, performanta raportata OUT-OF-SAMPLE. Cost 5 bps pe turnover.
Date: S&P daily 2013-18 (`data/sp500.csv`, gitignored).

## Verdict: NU bate buy-and-hold, fara edge de timing semnificativ

| Nume | SISTEM net OOS | SISTEM Sharpe | B&H Sharpe | edge_Sh | in-mkt | p |
|---|---|---|---|---|---|---|
| NVDA | +79.9% | +1.24 | **+2.33** | **−1.09** | 24% | 0.41 |
| AMZN | +92.0% | +1.98 | +1.61 | +0.36 | 27% | 0.017 |
| WMT | +24.8% | +0.98 | +0.82 | +0.16 | 13% | 0.043 |
| KO | +7.4% | +0.58 | +0.27 | +0.31 | 26% | 0.25 |
| MSFT | +18.4% | +0.78 | +1.29 | −0.52 | 34% | 0.62 |
| AMD | +22.7% | +0.49 | +1.37 | −0.88 | 13% | 0.53 |
| (restul) | … | … | … | **negativ** | … | >0.4 |

**edge_Sh (Sharpe sistem − Sharpe B&H) e negativ pe 9 din 12 nume.** Pe risc
ajustat, sistemul e mai prost decat a sta pur si simplu long. Exemplul brutal:
NVDA — sistemul +80%, dar buy-and-hold **+862%**; sistemul a stat in piata doar
24% din timp si a ratat fix marele trend pe care pretindea ca-l prinde.

## Testul care decide: POOLED

Un SINGUR test de permutare pe toate seriile OOS concatenate (rezolva testarea
multipla — nu 10 teste, ci unul pe tot portofoliul):

```
POOLED: net=+773% (beta de taur)  Sharpe=+0.67  zile=7548  p=0.210
```

**p=0.210 → timing NEDISTINS de noroc** la nivel de portofoliu. AMZN (p=0.017) si
WMT (p=0.043) per-nume sunt exact false-pozitivele asteptate din testarea
multipla (12 teste): se spala in agregat.

## Concluzie

Castigurile per-nume aparente erau (a) **beta de piata bull** (long cat timp
actiunile urcau) si (b) **artefacte de testare multipla**. Sistemul trend-pullback,
asa cum l-am definit, **nu adauga alpha de timing** peste buy-and-hold pe acest set
de date. Validarea onesta si-a facut treaba: a omorat un sistem care arata
promitator la prima vedere.

NU este consiliere de investitii. Artefact de cercetare descriptiv.
