# Buy-the-Dip prin CRIZE — rezultate (onest)

Reteaua e blocata in container (Stooq/Yahoo 403), dar aveam deja serii lungi care
traverseaza crahuri. `dipbuy` foloseste doar close, deci ruleaza pe ele.
Split 0.5 → felia OOS contine crizele (petrol 2008/2020, BTC 2018/2022).
Cost 5 bps. `longtest_cli.py`.

## Rezultate (OOS = a doua jumatate)

| activ | dip | trades | win% | PF | exp/tr | SIS net | SIS DD | B&H net | B&H DD | p |
|---|---|---|---|---|---|---|---|---|---|---|
| WTI | — | — | — | — | — | **INVALID** (pret <=0 in 2020) | | | | |
| BRENT | 0.2 | 95 | 61% | **0.93** | −0.19% | −61% | −94% | +82% | −94% | 0.71 |
| BTC | 0.4 | 22 | 73% | **8.69** | +5.45% | +198% | **−25%** | +1035% | **−77%** | **0.004** |

WTI exclus corect: petrolul a fost negativ in apr. 2020 → randamentele explodeaza,
backtest fara sens (garda in cod).

## Doua povesti opuse

**BRENT (39 ani): buy-the-dip PIERDE.** PF 0.93 (<1 = neprofitabil), net −61%
cat timp a sta long facea +82%. p=0.71 → zero edge. Pe petrol, „cumpara cat e jos"
e o capcana: petrolul are cicluri lungi, dipul devine dip mai adanc.

**BTC (OOS 2017-2026, include crahurile −84% 2018 si −77% 2022):** primul rezultat
cu edge REAL si relevant pentru RGTI:
- **p=0.004** — timing distins de noroc (rezista chiar si la corectie Bonferroni
  pe 3 active: 0.004×3 = 0.012 < 0.05).
- **max drawdown −25% vs −77% buy-and-hold** — sistemul a injumatatit-si-mai-bine
  pierderea in crahuri. Asta e valoarea reala cand ti-e frica de „cutit care cade".
- PF 8.69, win 73%, expectancy +5.45%/tranzactie — profitabil.
- DAR: net +198% vs B&H +1035% — castigi de ~5× mai putin decat a sta long. Doar
  22 tranzactii in 16 ani (dip=0.4 = cumpara doar caderi de 40%).

## Concluzia (raspuns la "cumparam cat e jos?")

Pe un activ volatil-speculativ (BTC ≈ profilul RGTI), „cumpara dipul ADANC" (−40%):
- e singura regula testata care arata **timing semnificativ** (p=0.004), nu drift;
- **controleaza dramatic drawdown-ul** (−25% vs −77%) — exact riscul de la
  cutitul care cade;
- dar e o strategie de **CONTROL AL RISCULUI**, nu de imbogatire: ratezi
  rachetele (faci 1/5 din buy-and-hold).

Pe un activ ciclic (petrol), aceeasi regula e neprofitabila (Brent PF 0.93).
Deci „cumpara cand e jos" NU e universal — depinde de activ, si chiar si unde
merge (BTC) e o frana de risc, nu un accelerator de profit. NU consiliere de
investitii.
