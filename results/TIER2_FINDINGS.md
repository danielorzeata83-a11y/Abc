# TIER 2 — rezultate (factori dincolo de microstructura TIER 1)

Toate cifrele sunt din motorul de validare A→E pe date reale. **NU este consiliere
de investiții. Artefact de cercetare.**

## Context

TIER 1 = 13 indicatori de microstructură (own-price), deja validați. TIER 2 = restul
familiei de factori a proiectului (trend, reversal, vol-managed, low-vol, calendar,
plus illichiditate și residual-momentum). Întrebarea: au edge real, testați corect?

## TIER 2 — factori time-series pe watchlist (5 nume: NVDA AAPL MSFT AMD TSLA)

`python validate_cli.py --indicators tier2` (4780 zile pooled)

- Niciun factor semnificativ. Ansamblu Sharpe ~0.05, p≈0.5 → nedistingibil de noroc.
- `low_vol` are cel mai mare |IC| (−0.06 la h=21) dar **negativ**: pe aceste growth-uri,
  vol mare a însoțit randamente mai mari (efect de beta).
- Lecție metodologică: reversal/momentum/low-vol sunt anomalii **cross-secționale**;
  testate ca semnal time-series pe câteva nume corelate → zgomot.

## TIER 2b — factori cross-secționali pe univers (S&P500, 470 nume, 2013–18)

`python validate_xs_cli.py` — long-short, **net de costuri** (10 bps), Sharpe full/OOS + sign-flip p.

| factor   | Sharpe full | Sharpe OOS | p_OOS | citire |
|----------|------------:|-----------:|------:|--------|
| amihud   | +0.76 | **+0.91** | 0.099 | cel mai bun; ține OOS; marginal semnificativ |
| momentum | +0.48 | **+0.77** | 0.163 | pozitiv, ține OOS, promițător |
| resmom   | +0.17 | +0.00 | 0.50 | dispare după costuri |
| low_vol  | −0.69 | −0.93 | 0.90 | negativ (bull 2013–18, high-beta a câștigat) |
| reversal | −2.67 | −2.53 | 1.00 | distrus de turnover (rebalansare zilnică) |

→ **amihud și momentum** sunt singurii cu edge OOS pozitiv; niciunul la p<0.05
(„promițător, nu dovedit"). Testat corect, edge-ul apare — vs TIER 2 unde era zgomot.

## #3 — factori time-series pooled pe tot universul (501 nume)

`python validate_universe_cli.py --indicators tier2`

| factor      | IC h=1 | IC h=5 | IC h=21 | citire |
|-------------|-------:|-------:|--------:|--------|
| ts_reversal | +0.031 | +0.037 | +0.049 | pozitiv, consistent, robust pe ambele regime |
| ts_momentum | −0.040 | −0.071 | −0.110 | negativ la nivel de acțiune zilnică (reversal domină) |
| vol_managed | −0.024 | −0.060 | −0.070 | — |
| low_vol     | −0.014 | −0.035 | −0.036 | — |

- Pooling-ul pe 501 nume **a făcut vizibil `ts_reversal`** (era zgomot pe 5 nume).
- Ansamblul equal-weight iese negativ — dar **artefact**: motorul mediază semnalele
  fără să le alinieze la semnul IC, deci componenta cu IC negativ trage în jos. IC-ul
  e gross (fără costuri); reversal-ul, ca strategie tradabilă, depinde de turnover.

## Defect de motor identificat (next)

Ansamblul equal-weight nu aliniază semnele la IC. Un combinator **sign-aware**
(ponderi ∝ semnul/mărimea IC out-of-sample) ar reflecta corect informația factorilor.

## Verdict

Consecvent cu `REPORT.md`: majoritatea factorilor nu produc edge tradabil curat.
Singurele semnale care supraviețuiesc testului onest: **amihud și momentum
cross-secțional** (OOS Sharpe ~0.8–0.9, gross/aproape de costuri) și **ts_reversal**
ca IC pe univers larg. Nimic la semnificație p<0.05.
