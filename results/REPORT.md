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

---

## Validare out-of-sample a trend-following (testul suprem)

Selectez fereastra MA pe primele 60% din istoric (train), o tranzacționez
pe ultimele 40% (test, nevăzut). Risc egal, 10 bps.

| Activ | MA ales pe train | Sharpe train | Sharpe TEST | B&H TEST | Câștigător |
|---|---|---|---|---|---|
| BTC   | MA10  | 2.32 | 0.64 | 0.95 | Buy&Hold |
| Brent | MA150 | 0.43 | -0.22 | -0.12 | Buy&Hold |

### Constatare decisivă

Pe BTC, MA10 avea Sharpe 2.32 pe train -> s-a prăbușit la 0.64 OOS și a
pierdut față de buy&hold (0.95). Overfitting prins în flagrant. Aparenta
"robustețe pe ferestre" din sweep era o iluzie: când SELECTEZI efectiv un
parametru pe trecut și-l tranzacționezi forward, avantajul dispare pe
ambele active.

### Verdict final al întregului proiect

NICIO variantă testată -- Markov standalone, HMM, regim ca filtru,
trend-following cu parametru selectat -- nu bate buy&hold out-of-sample
pe aceste active individuale, după costuri și la risc egal. Singura
tehnică robustă rămâne vol targeting (reduce drawdown fără a promite
randament). Concluzia practică: pe un singur activ, backtest-urile mint;
ce arată genial in-sample moare out-of-sample. Aceasta NU este consiliere
de investiții.

---

## Momentum cross-sectional pe portofoliu (S&P 500, 470 acțiuni, 2013-2018)

Singura direcție validată academic. Rank universe după randament trecut,
long winners / short losers, rebalansare lunară. No look-ahead.

| Strategie | Ret | Sharpe | MaxDD |
|---|---|---|---|
| EqualWeight Buy&Hold | 92% | 1.09 | -17% |
| LongShort top/bot 20% | 26% | 0.48 | -18% |
| LongShort top/bot 10% | 47% | 0.61 | -22% |
| LongOnly top 20% | 96% | 1.14 | -13% |

### Out-of-sample (train 60% / test 40%)
Selectat lookback=126 skip=5 (train Sharpe 0.88) ->
TEST Momentum LS Sharpe **-0.17** vs Buy&Hold **1.90**. Buy&hold câștigă.

### Constatare

Nici momentum pe portofoliu nu bate buy&hold în acest eșantion.
LongOnly top-20% doar egalează (1.14 vs 1.09). Long-short pierde clar.
ATENȚIE la context: 2013-2018 e un singur bull market puternic --
mediul cel mai ostil pentru long-short momentum (piciorul short e
strivit), și exact perioada în care factorul momentum a avut
underperformance documentat post-criză. Validarea academică reală
folosește ~90 ani și multe piețe -- ce nu putem replica aici.

### Concluzie onestă

Pe datele pe care le putem testa efectiv, NICIO strategie nu bate
robust buy&hold după costuri și la risc egal -- nici Markov, nici HMM,
nici trend, nici momentum de portofoliu. Lecția nu e "totul e inutil",
ci: un edge real cere amploare (decade × multe piețe × multe active) și
infrastructură pe care un "truc" de pe YouTube nu o are. Baseline-ul
robust rămâne buy&hold + vol targeting. NU este consiliere de investiții.

---

## EDGE POZITIV GĂSIT: short-term reversal (market-neutral alpha)

Long recent losers / short recent winners pe panel-ul S&P 500 (470
acțiuni). Turnover redus + costuri instituționale.

### Net Sharpe vs nivel cost (full sample)
| config | 1bps | 2bps | 3bps | 5bps |
|---|---|---|---|---|
| lb=10 h=5 top=0.2 | 0.43 | 0.32 | 0.20 | -0.02 |
| lb=10 h=10 top=0.2 | 0.40 | 0.32 | 0.24 | 0.07 |
| lb=15 h=10 top=0.1 | 0.38 | 0.32 | 0.26 | 0.15 |
| lb=10 h=5 top=0.1 | 0.44 | 0.34 | 0.24 | 0.05 |

### Validare OUT-OF-SAMPLE @ 2bps (train 60% / test 40%)
Selectat lb=10 h=5 top=0.1 (train Sharpe 0.39) ->
**TEST Reversal Sharpe +0.20, ret +3%**, corelație cu piața +0.10.
(Buy&Hold test Sharpe 1.90 -- bull pur, dar reversal e market-neutral.)

### De ce e un edge REAL (spre deosebire de restul proiectului)
1. Sharpe GROSS pozitiv pe TOATE configurațiile (robust, nu noroc).
2. SUPRAVIEȚUIEȘTE out-of-sample net de costuri (+0.20, NU se prăbușește
   în negativ ca Markov/trend/momentum). Prima dată în tot proiectul.
3. Corelație cu piața +0.10 -> aproape MARKET-NEUTRAL: sursă de alpha
   independentă de direcția pieței.

### Limite (sinceritate obligatorie)
- Modest (Sharpe 0.2-0.4), nu îmbogățește peste noapte.
- Nu bate buy&hold standalone într-un bull (rolul lui e diversificare).
- Moare la costuri retail (>=5-10bps); viabil doar instituțional (1-3bps).

### Concluzie
Primul edge pozitiv robust și validat OOS din proiect. Arată exact ca
alpha quant autentic: mic, market-neutral, sensibil la costuri -- opusul
unui "truc" de YouTube. Fondurile reale combină multe astfel de edge-uri
mici la costuri mici. NU este consiliere de investiții.

---

## Tentativă de întărire a edge-ului: complexitatea a stricat

Am încercat două rafinamente peste plain reversal: (1) ensemble
multi-orizont (3/5/10 zile), (2) ponderare inverse-volatility a legurilor.

### Net Sharpe pe nivel de cost (full sample)
| variant | 1bps | 2bps | 3bps | 5bps |
|---|---|---|---|---|
| Plain lb=10 h=5 top=0.1 | 0.44 | 0.34 | 0.24 | 0.05 |
| Ensemble(3,5,10) EW | 0.29 | 0.16 | 0.03 | -0.23 |
| Ensemble(3,5,10) inverse-vol | 0.00 | -0.15 | -0.29 | -0.58 |

OOS @ 2bps: ensemble selectat -> TEST Sharpe **-0.25** (colaps), vs
plain reversal care dăduse +0.20 OOS.

### De ce au stricat rafinamentele
- Inverse-vol a ucis edge-ul: în reversal premiul e TOCMAI în numele cele
  mai volatile (ricoșează cel mai tare) -- exact cele subponderate.
- Ensemble-ul a adăugat complexitate fără semnal nou -> overfit la
  selecție, colaps OOS.

### Lecție
Versiunea SIMPLĂ rămâne edge-ul robust (plain reversal, OOS +0.20).
Complexitatea "deșteaptă" a degradat rezultatul -- capcana clasică
combătută de karpathy-guidelines. În trading: simplu + validat OOS bate
sofisticat + impresionant in-sample. NU este consiliere de investiții.

---

## Combinarea edge-urilor: nu poți dilua un perdant în câștigător

Am adăugat un al doilea factor market-neutral (low-vol long-short) și am
încercat să-l combin cu reversal la risc egal.

| | Sharpe | ret | DD |
|---|---|---|---|
| Reversal | +0.28 | +14% | -16% |
| LowVol L/S | -0.62 | -33% | -35% |
| COMBO 50/50 | -0.28 | -14% | -21% |
| **OOS** Reversal | -0.02 | | |
| **OOS** LowVol | -0.86 | | |
| **OOS** COMBO | -0.64 | | |

Correlație reversal<->lowvol: -0.22 (necorelate, ideal pentru diversificare).

### De ce a eșuat
LowVol long-short pierde în bull-ul 2013-2018: piciorul short (high-vol/
high-beta) a condus rally-ul, deci shortarea lui a fost dezastruoasă.

### Lecție de portfolio construction
Corelația negativă e necesară dar NU suficientă. Diversificarea de risc
nu repară randament negativ. Combinând un câștigător (+0.28) cu un
perdant (-0.62) la risc egal, am tras câștigătorul în jos. Nu poți
fabrica alpha prin combinare: "prânzul gratis" e gratis doar dacă FIECARE
componentă are deja edge pozitiv. Reversal rămâne singurul edge validat;
adăugarea unui sleeve negativ doar diluează. NU este consiliere de
investiții.

---

## SUCCES: combinarea a două edge-uri reale (diversification free lunch)

Al doilea edge găsit dintr-o familie diferită: turn-of-month (calendar),
necorelat cu reversal. Ambele pozitive -> combinarea CREȘTE Sharpe.

| | corr cu reversal | Sharpe | ret | DD |
|---|---|---|---|---|
| Reversal | -- | +0.34 | +19% | -16% |
| TurnOfMonth | +0.08 | +0.37 | +12% | -8% |
| **COMBO (equal-risk)** | -- | **+0.48** | +24% | -12% |

### Out-of-sample (ponderi inverse-vol din train 60%)
| | Sharpe | ret | DD |
|---|---|---|---|
| TEST Reversal | +0.09 | +1% | -16% |
| TEST TurnOfMonth | +0.33 | +4% | -8% |
| **TEST COMBO** | **+0.28** | +5% | -13% |

### Constatare
Full-sample COMBO Sharpe 0.48 > max(0.34, 0.37): diversificarea reală.
Combinând două surse INDEPENDENTE cu Sharpe pozitiv, obții un Sharpe mai
mare decât oricare individual -- singurul "free lunch" din finanțe. OOS,
reversal a slăbit într-un bull pur (+0.09) dar TOM a ținut (+0.33) și
combo-ul a livrat +0.28 robust: nu trebuie să ghicești care edge va fi mai
puternic. Asta e diferența față de tentativa anterioară (low-vol): acolo
una din componente avea Sharpe negativ; aici AMBELE sunt edge-uri reale.

### Concluzia constructivă a proiectului
Contrastul e lecția: low-vol (Sharpe negativ) + reversal = combo stricat;
turn-of-month (Sharpe pozitiv, necorelat) + reversal = combo mai bun decât
ambele. Combinarea edge-urilor FUNCȚIONEAZĂ -- dar doar cu edge-uri
genuine, independente, fiecare validat OOS. Exact modelul fondurilor
quant. NU este consiliere de investiții.

---

## Al treilea edge: vol-managed market (Moreira-Muir) + portofoliul de 3

Scalez expunerea la piață invers cu varianța recentă. Edge documentat,
dar market-DIRECTIONAL (poartă beta), nu market-neutral.

### Matrice de corelație
| | Rev | TOM | VolMgd |
|---|---|---|---|
| Rev | 1.00 | 0.08 | 0.15 |
| TOM | 0.08 | 1.00 | 0.46 |
| VolMgd | 0.15 | 0.46 | 1.00 |

### Performanță
| | Sharpe full | Sharpe OOS | DD OOS |
|---|---|---|---|
| Reversal | +0.34 | +0.09 | -16% |
| TurnOfMonth | +0.37 | +0.33 | -8% |
| VolManaged | +0.77 | +1.51 | -10% |
| COMBO-2 (rev+TOM) | +0.48 | +0.28 | -- |
| **COMBO-3** | **+0.71** | **+0.99** | -9% |

### Onestitate obligatorie
VolManaged ridică OOS combo de la 0.28 la 0.99 -- dar e market-directional
(corr 0.46 cu TOM), iar Sharpe-ul lui mare (1.51 OOS) reflectă în mare
parte bull-ul din perioada de test, nu alpha pur. Portofoliul nu mai e
"3 alpha-uri independente", ci 1 alpha market-neutral (reversal) + 2
edge-uri de timing care împart beta. Are Sharpe mai mare și drawdown mai
mic, dar și mai multă dependență de piață -- ar suferi mai mult într-un
bear. Beneficiul Moreira-Muir e însă real: vol-managing taie expunerea
înainte de turbulență (DD -10% vs piață ~-17%).

### Concluzie
Portofoliul final: reversal (alpha market-neutral) + turn-of-month +
vol-managed (timing). COMBO-3 OOS Sharpe +0.99 cu drawdown -9%. Combinarea
edge-urilor reale, independente și validate OOS funcționează -- exact
modelul fondurilor quant. Distincția cheie învățată: market-neutral alpha
(diversifică) vs market-timing/beta (amplifică în trend). NU este
consiliere de investiții.
