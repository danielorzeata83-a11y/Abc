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

> **Atenție la comparabilitate:** acest tabel per-factor folosește lungimea proprie a
> fiecărui stream (warmup diferit → `n_zile` diferă pe linii). Tabelul **blend** de mai
> jos taie la coada comună cea mai scurtă, deci Sharpe-urile lui NU sunt pe aceeași
> fereastră cu cele de aici. Nu le citi ca o singură coloană continuă.

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

## Defect de motor identificat ȘI reparat

Ansamblul equal-weight nu alinia semnele la IC → componenta cu IC negativ (momentum)
trăgea în jos componenta cu IC pozitiv (reversal). Adăugat `ensemble.sign_aware_signal`:
ponderează fiecare indicator cu corelația lui **cauzală** față de randamentul next-day
(perechi cunoscute strict înainte de t → fără look-ahead); factorii invers-predictivi
sunt întorși automat. `evaluate_ensemble(..., weighting="ic")`; raportul afișează rândul
`sign-aware IC` lângă equal-weight și gated.

Rezultat pe univers (501 nume, walk-forward):

| ansamblu | Sharpe | p |
|----------|-------:|---:|
| equal-weight neconditionat | −0.31 | 0.72 |
| gated meanrev | −0.14 | 0.61 |
| **sign-aware IC** | **+0.05** | 0.46 |

→ Fix-ul corectează semnul (−0.31 → +0.05), dar **nu fabrică alfa**: rămâne
nesemnificativ (p=0.46). Defectul metodologic e rezolvat; edge real tot nu există
la p<0.05 pe acești factori time-series. Motorul rămâne onest.

## Blend sign-aware al factorilor cross-secționali (conviction)

`python validate_xs_cli.py` — secțiunea blend. Ponderi ∝ Sharpe **in-sample** (partea
pozitivă, normalizată), evaluat OOS. Factorii care pierd in-sample primesc zero — NU
se short-ează un portofoliu dominat de costuri (sign-flip ar plăti același turnover).

| factor   | w | Sharpe_in |
|----------|--:|----------:|
| amihud   | 0.65 | +1.19 |
| momentum | 0.19 | +0.35 |
| resmom   | 0.16 | +0.29 |
| reversal | 0.00 | −2.43 (zero-uit) |
| low_vol  | 0.00 | −0.23 (zero-uit) |

**BLEND OOS: Sharpe +0.56, p=0.236, 444 zile.**

- Combinatorul identifică singur amihud ca dominant (0.65) și zero-uiește pierzătorii —
  fără leak. Metoda e corectă.
- Blend-ul (+0.56) e sub amihud singur (+0.91), dar pe fereastră mai scurtă (coada
  comună 444 zile vs 495) și diluat de resmom (~0 OOS).
- p=0.236 → **promițător, nu dovedit**. Limitarea reală e istoricul scurt: datasetul
  Kaggle e 2013–18, OOS ≈ 1.8 ani — prea puțin ca un Sharpe 0.56 să fie semnificativ.

## Note de onestitate (caveats)

- **`vol_managed` și `low_vol` sunt cvasi-identice** — ambele sunt ±deviația standard a
  randamentelor (ferestre diferite: 20 vs 60). Sub IC pe ranguri sunt aproape redundante;
  tabelele le listează separat doar pentru transparență, nu ca semnale independente.
- **`turn_of_month`** e în `tier2.INDICATORS` și trece prin motor, dar nu apare în
  tabelele de rezultate (IC ~0 pe orizonturi) — inclus pentru completitudine, fără edge.
- Ferestrele tabelelor TIER 2b (per-factor vs blend) diferă — vezi avertismentul de la
  secțiunea TIER 2b.

## Verdict

Consecvent cu `REPORT.md`: majoritatea factorilor nu produc edge tradabil curat.
Singurele semnale care supraviețuiesc testului onest: **amihud și momentum
cross-secțional** (OOS Sharpe ~0.8–0.9, gross/aproape de costuri) și **ts_reversal**
ca IC pe univers larg. Nimic la semnificație p<0.05.
