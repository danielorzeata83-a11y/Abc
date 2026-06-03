# Trend overlay: hindsight vs real-time „când a fost sigur de cumpărat"

**Data:** 2026-06-03
**Status:** design aprobat, în așteptarea review-ului specului

> Artefact de cercetare/educație. **NU este consiliere de investiții.**

## Problema

Privind un grafic NVDA, e tentant să spui „de aici în sus a fost bull, aici era
sigur de cumpărat". Asta se vede **perfect doar în hindsight**. În timp real,
orice indicator de trend fie întârzie (confirmă după ce prețul a urcat deja),
fie dă semnale false (whipsaw). Scopul: un grafic care arată **diferența** —
adevărul de după vs. ce ți-ar fi spus indicatorii live — ca lecție de disciplină.

## Domeniu & date

- Ticker: NVDA (configurabil), din `data/sp500.csv` (2013–2018, OHLC + volum).
- Folosim close-ul zilnic și datele.
- **Regulă de aur:** tot ce e „real-time" folosește DOAR trecutul la fiecare zi
  (fără look-ahead). Altfel mințim despre ce ai fi putut face live.

## Cele trei (patru) straturi pe grafic

### Strat HINDSIGHT (adevărul — verde)
- `hindsight_bottom()` — minimul major dinaintea marelui rally (fundul real).
- Marcaj vertical + etichetă „fundul real: $X la data Y" = „de aici în sus a fost bull".

### Strat REAL-TIME (cauzal — ce ți-ar fi spus indicatorii)
- **SMA 50 & SMA 200** desenate ca linii.
- **Golden cross** (SMA50 trece peste SMA200) = „bull confirmat";
  **Death cross** (invers) = „bear". Markere pe grafic.
- **Benzi de fundal = regimul HMM walk-forward** (bull/sideways/bear) pe zi —
  reantrenat doar pe trecut (onest, fără look-ahead).

### Strat LECȚIE (de ce contează)
- **Costul întârzierii** (`lag_cost()`): cât a urcat NVDA între *fundul real* și
  *ziua primului golden cross* → „ai fi ratat +X% așteptând confirmarea".
- **Semnale false** (`count_whipsaws()`): câte cruci s-au inversat repede.

### Strat DRAWDOWN (durerea indicatorului)
- `signal_drawdown()`: după ce golden cross te-a băgat în piață, care a fost cel
  mai mare drawdown pe care l-ai îndurat înainte de death cross / final →
  „indicatorul te-a băgat, apoi ai stat printr-o scădere de −Y%".

## Decizii de onestitate (aprobate)

1. **Golden cross** e 100% cauzal (medii din trecut) ✅.
2. **HMM walk-forward** (nu in-sample): regimul se reantrenează pe fereastră
   expandabilă de trecut, fără să vadă viitorul. Mai puțin „frumos" vizual decât
   in-sample, dar onest.

## Arhitectură & cod (chirurgical, refolosește ce există)

### Modul nou: `markov/trend_overlay.py` (funcții pure, testabile)
- `sma(prices, window) -> np.ndarray` — medie mobilă simplă (NaN pe warmup).
- `sma_crossovers(prices, fast=50, slow=200) -> list[Crossover]` — evenimente
  golden/death cu (index, dată-index, tip). Cauzal.
- `hindsight_bottom(prices) -> int` — indexul fundului major (minimul global pe
  fereastra dată; v1: minimul global, simplu și fără parametri de tunat).
- `lag_cost(prices, bottom_idx, first_golden_idx) -> float` — randamentul
  procentual între fund și prima confirmare golden cross.
- `count_whipsaws(crossovers, min_hold_days) -> int` — cruci inversate sub un
  prag de zile (semnale false).
- `signal_drawdown(prices, entry_idx, exit_idx) -> float` — max drawdown între
  intrare (golden) și ieșire (death/final).

### Adăugire în `markov/hmm_walkforward.py`
- `hmm_walk_forward_states(prices, warmup=250, refit_every=60, seed=None,
  _fit_fn=None) -> (states, start_index)` — aceeași buclă de reantrenare ca
  `hmm_walk_forward_positions`, dar colectează `today_state` (eticheta de regim
  pe zi) în loc de poziție. Funcția-soră, fără să dublăm logica de fit.

### Renderer SVG nou: `markov/trend_chart.py`
- `render_trend_svg(dates, close, sma_fast, sma_slow, crossovers, hmm_states,
  bottom_idx, stats) -> str` — extinde stilul din `svg_chart.py`:
  linia prețului + 2 linii MA + benzi de fundal colorate pe regim +
  markere cruci + marcaj fund hindsight + legendă + caseta-lecție + disclaimer.

### CLI nou: `trend_cli.py`
- `python trend_cli.py --ticker NVDA --data data/sp500.csv [--out trend_NVDA.html]`
- Încarcă seria, calculează straturile, scrie HTML self-contained.
- Conține mereu `DISCLAIMER`.

## Testare (TDD, red-green-refactor)

Funcții pure în `tests/test_trend_overlay.py`:
- `sma` corect pe serie cunoscută; NaN pe warmup.
- `sma_crossovers`: serie sintetică cu o încrucișare cunoscută → un golden la
  indexul așteptat; nicio cruce pe serie monotonă.
- `hindsight_bottom`: minimul global pe serie „V".
- `lag_cost`: pe fund + index cunoscut → procent exact.
- `count_whipsaws`: cruci dese sub prag → numărate; cruci rare → 0.
- `signal_drawdown`: pe serie cunoscută → drawdown exact.
- `hmm_walk_forward_states`: cu `_fit_fn` injectat (fără hmmlearn real) →
  lungime corectă, fără look-ahead, mapare la State.

Render: `tests/test_trend_chart.py` — SVG conține `<polyline>`-urile MA,
markerele așteptate, eticheta fundului și `DISCLAIMER`.

## Out of scope (YAGNI v1)
- Alți indicatori (RSI/MACD) — există în `indicators.py`, dar nu-i suprapunem acum.
- Multi-ticker pe același grafic.
- Tunarea ferestrelor MA/HMM (folosim valori a-priori standard: 50/200, warmup 250).

## Disclaimer
Suprapunerea hindsight/real-time e o **vizualizare educativă**, nu o strategie
validată. Întârzierea și whipsaw-urile arătate sunt exact motivul pentru care
„timing-ul" e greu. **NU este consiliere de investiții.**
