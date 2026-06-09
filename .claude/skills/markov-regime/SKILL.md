---
name: markov-regime
description: Detectează regimul de piață al unui simbol folosind uneltele proiectului Abc — stări Markov BULL/SIDEWAYS/BEAR (matrice de tranziție + forecast n-zile + distribuție staționară), regim Hurst (trend vs mean-revert) și semnalul de volatilitate (z realized_var). Folosește când utilizatorul întreabă „în ce regim e X", „bull sau bear", „trend sau range", cere o matrice de tranziție / forecast de stări, sau o citire de regim pentru un ticker. Pe date REALE (cache backfilled sau CSV OHLCV). NU consiliere de investiții.
---

# markov-regime

Citire DESCRIPTIVĂ a regimului de piață pentru un simbol, din componentele deja
validate ale proiectului. Trei lentile complementare:

1. **Stări Markov** (`markov.states` + `markov.transition`): clasifică fiecare zi în
   BULL / SIDEWAYS / BEAR (suma randamentelor pe fereastră vs prag), construiește
   matricea de tranziție, prezice distribuția la 1 și n zile, și distribuția staționară.
2. **Regim Hurst** (`markov.validation.regime.hurst_regime`): `trend` (H>0.5, favorabil
   momentum) vs `meanrev` (H<0.5, favorabil reversal).
3. **Volatilitate** (`z realized_var`, cauzal): RIDICATĂ (≥+1) = risc forward mai mare.
4. **Backtest walk-forward** (`markov.regime_backtest`): semnalul P(BULL)-P(BEAR),
   re-estimat la fiecare pas DOAR din trecut (fără look-ahead) → Sharpe + max drawdown.
5. **HMM opțional** (`markov.hmm`, hmmlearn): regimuri ascunse (Baum-Welch + Viterbi),
   cu randamentul mediu per stare. Degradare curată dacă hmmlearn lipsește.

## Cum rulezi

Scriptul împachetat face totul. Are nevoie de date REALE — fie cache daily backfilled
(`--data-dir`), fie un CSV long OHLCV (`--universe`, ex. `data/sp500.csv`):

```bash
python .claude/skills/markov-regime/scripts/regime.py --symbol AAPL --universe data/sp500.csv
python .claude/skills/markov-regime/scripts/regime.py --symbol NVDA --data-dir data/intraday
```

Opționale: `--window 20` (fereastra de clasificare), `--threshold 0.05` (pragul
bull/bear pe suma randamentelor), `--horizon 5` (orizontul forecast-ului),
`--no-backtest` (sari peste walk-forward), `--no-hmm` (sari peste HMM).

Dacă lipsesc datele: rulează întâi `backfill_cli.py` (vezi `docs/CLIS.md`) pentru
`--data-dir`, sau folosește `data/sp500.csv` pentru `--universe`.

## Cum interpretezi (onest)

- Citește STAREA curentă + `P(mâine|azi)`: dacă rândul e aproape uniform (~0.33 fiecare),
  tranziția e ne-informativă — nu supra-interpreta.
- `trend` (Hurst) sugerează că momentum-ul are mai mult sens decât reversal-ul în acel
  regim, și invers; coroborează cu rezultatele din `results/TIER2_FINDINGS.md`.
- Vol RIDICATĂ → micșorează convingerea / expunerea (semnal de risc, nu de direcție).

## Avertisment obligatoriu

Metoda Markov bull/sideways/bear **NU a produs un edge tradabil** pe niciun activ testat
în proiect (`results/REPORT.md`). Raportul e **descriptiv** — o hartă a regimului, nu un
semnal de tranzacționare. Fiecare ieșire poartă „NU este consiliere de investiții".
Nimic aici nu e point-in-time / fără bias de supraviețuire.
