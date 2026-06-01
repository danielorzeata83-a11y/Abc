# Raport de test — Metoda Markov "hedge fund" pe active multiple

Research engine TDD (63 teste). Date reale, walk-forward strict (fără
look-ahead), costuri 10 bps, comparație și pe risc egal (20% vol țintă).

## Rezumat executiv

Metoda Markov (bull/sideways/bear + matrice de tranziție + semnal
P_bull−P_bear) **nu produce un edge tradabil pe niciun activ testat**.
Pe BTC e dominată de buy & hold; pe petrol pierde bani în formă brută.
Singura tehnică cu valoare reală descoperită în tot proiectul este
**volatility targeting** (management de risc), nu metoda în sine.

---

## Rezultate pe active

### BTC (2010–2026, 5789 zile) — activ puternic trendant

| Strategie | Randament net | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| Buy & Hold | 129.855.398% | 1.44 | −93% | 1 |
| Markov (10bps) | 3.079.531% | 1.24 | −73% | 5707 |
| **Egal-risc** Buy&Hold | 19.424% | **1.57** | −39% |
| **Egal-risc** Markov | 17.479% | 1.48 | −41% |

- Timing OOS semnificativ (p=0.0005), dar irelevant practic.
- La risc egal, buy & hold câștigă pe TOATE axele.
- HMM walk-forward (pasul 10): **−95%**, dovadă de overfitting.

### WTI oil (1986–2026, 10.167 zile) — activ mean-reverting

| Strategie | Randament net | Sharpe | MaxDD |
|---|---|---|---|
| Buy & Hold | 399% | 0.31 | −94% |
| Markov (10bps) | **−97%** | 0.01 | −95% |
| Egal-risc Buy&Hold | 142% | 0.21 | −65% |
| Egal-risc Markov | −68% | −0.05 | −78% |

- Semnificație: p=0.5727 → **nesemnificativ** (timing = zero, pur noroc).
- 9945 trades — semnal extrem de nervos, mâncat de costuri.
- Markov pierde 97% din capital. Dezastru.

### Brent oil (1987–2026, 9898 zile) — activ mean-reverting

| Strategie | Randament net | Sharpe | MaxDD |
|---|---|---|---|
| Buy & Hold | 439% | 0.31 | −94% |
| Markov (10bps) | −15% | 0.26 | −79% |
| Egal-risc Buy&Hold | 65% | 0.16 | −76% |
| Egal-risc Markov | 14% | 0.11 | −67% |

- Semnificație: p=0.0500 → **la limită** (slab, nu de încredere).
- La risc egal: Markov are DD ușor mai mic (−67% vs −76%) dar
  randament mult mai mic (14% vs 65%). Nu compensează.

---

## Concluzii dovedite cu date

1. **"Win every trade" este fals.** Demonstrat pe 3 active.
2. **Pe activ trendant (BTC):** Markov pierde clar față de buy & hold.
3. **Pe activ mean-reverting (petrol):** ipoteza că Markov ar merge mai
   bine pe range-bound **NU se confirmă**. WTI: nesemnificativ, −97%.
   Brent: la limită, tot pierzător față de buy & hold.
4. **HMM (pasul 10) out-of-sample:** −95%, overfitting clasic.
5. **Definiția stării e fragilă:** threshold vs HMM = 23% acord.
6. **Costurile ucid metoda:** ~10.000 trades pe petrol.

## Ce funcționează cu adevărat

**Volatility targeting** — simpla scalare la risc constant a redus
drawdown-ul de la ~−93% la ~−40% (BTC) păstrând randamentul. Acesta este
singurul rezultat robust și valoros al proiectului, și e o tehnică
standard de risk management, complet independentă de metoda din video.

## Verdict final

> Metoda Markov "hedge fund" din video este un **exercițiu educațional
> solid** (matematica e corectă), dar **nu este o strategie pe care să
> pui bani reali**. Pe toate activele testate, după costuri și la risc
> egal, este dominată de cea mai simplă alternativă: buy & hold.
> Recomandare: a NU se folosi în trading real fără un edge fundamental
> nou. Nimic din acest raport nu constituie sfat de investiții.

---

## Combinații: regim ca filtru defensiv (pasul "păstrăm ce e bun")

Markov regime folosit corect (gate de risc peste o strategie de bază),
nu ca semnal de intrare. Risc egal 20% vol, 10 bps.

| Activ | Buy&Hold | BH+RegimeFilter | Trend(MA50) | Trend+Regime |
|---|---|---|---|---|
| BTC   | 19.424% / 1.57 / −39% | 22.715% / 1.54 / −41% | 126.378% / 1.57 / −62% | 120.788% / 1.56 / −63% |
| WTI   | 142% / 0.21 / −65% | **−52%** / 0.02 / −76% | −31% / 0.08 / −79% | −27% / 0.09 / −79% |
| Brent | 65% / 0.16 / −76% | **137%** / 0.21 / −58% | −12% / 0.11 / −80% | −48% / 0.08 / −80% |

(format: randament / Sharpe / MaxDD)

### Constatare

Filtrul de regim NU este robust: ajută pe Brent (137% vs 65%, DD
−58% vs −76%), strică grav pe WTI (−52% vs 142%), neutru pe BTC. Două
active aproape identice (WTI/Brent) dau rezultate OPUSE cu aceeași
metodă -- semnătura norocului, nu a unui edge real.

Trend-following (MA50) este de departe cel mai puternic semnal pe BTC
(126.378% la Sharpe 1.57), dar pierde pe petrol și nu beneficiază de
filtrul de regim.

### Verdict combinat

Nici ca filtru defensiv Markov nu adaugă valoare consistentă. Singurele
elemente robuste rămân: (1) vol targeting pentru control de risc, (2)
trend-following ca sursă de randament pe active trendante. Markov nu
intră în niciuna.
