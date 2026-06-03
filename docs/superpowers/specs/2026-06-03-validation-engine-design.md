# Spec: motor de validare a indicatorilor (agnostic) — v1 pe TIER 1

**Data:** 2026-06-03
**Branch:** `claude/upbeat-fermi-L3dat`
**Status:** design aprobat conceptual; în așteptarea revizuirii spec-ului scris.

> NU este consiliere de investiții. Acesta e un artefact de cercetare.

## Problemă & intenție

Avem 13 indicatori TIER 1 (`markov/intraday/indicators.py`) corecți tehnic și
testați, dar **nedovediți**: nu știm dacă vreunul prezice ceva pe datele reale.
Riscul nu e bug-ul în cod, ci construirea unui panou sofisticat fără putere
predictivă.

Observația cheie a utilizatorului: **un indicator testat singur poate părea mort,
dar o „echipă" de indicatori oferă altă perspectivă** — prin ortogonalitate
(adaugă peste restul), comutare pe regim (spune *când* merge alt alpha) sau
interacțiuni. Deci validarea trebuie să măsoare atât piesa singură, cât și
echipa, în ordinea corectă, fără să ne mințim prin overfit.

**Scope v1:** un motor **agnostic** (ia *orice* set de indicatori + simboluri) care
produce un raport de validare; primul „client" sunt cei 13 din TIER 1. Se
refolosește la TIER 2 fără rescriere.

## Decizii de design (confirmate)

1. **Țintă:** randament forward pe **mai multe orizonturi** cu accent pe **zilnic**;
   orizonturi `(1, 5, 21)` zile (1 zi, ~săptămână, ~lună). Daily se derivă din
   cache-ul 15m. (Decizie „C, accent pe zilnic".)
2. **Date IC:** **pooled time-series** — IC time-series per simbol, mediat peste
   watchlist (NVDA, AAPL, MSFT, AMD, TSLA) cu dispersie. Protejează împotriva
   concluziei „noroc NVDA"; cross-section pur pe 5 simboluri ar fi prea fragil.
   (Decizie „C pooled".)
3. **Combinare (ansamblu):** **equal-weight pe z-score = baseline cinstit**; orice
   metodă mai complexă (regresie regularizată) **trebuie să bată baseline-ul
   out-of-sample** ca s-o păstrăm, altfel se aruncă. (Decizie „C, A ca adevăr de
   bază" — testul karpathy: complexitatea se plătește singură sau moare.)

## Principiu metodologic — pași A→E (ordinea contează)

| Pas | Ce măsoară | Natură | De ce |
|---|---|---|---|
| **A. IC individual + decay** | are *vreun* semnal, pe ce orizont | descriptiv | harta fiecărei piese; NU tăiem aici |
| **B. matrice corelație + familii** | cine repetă pe cine | descriptiv | din 13 rămân poate ~5 familii |
| **C. IC marginal/incremental** | cât adaugă fiecare *peste* restul | descriptiv | aici prinzi slab-dar-ortogonal |
| **D. IC condiționat pe regim** | alpha × regim | descriptiv | aici prinzi „comutatoarele" |
| **E. ansamblu walk-forward** | echipa, OOS | **pretinde edge** | singurul pas care afirmă ceva tranzacționabil |

**Linia roșie:** pașii A–D sunt descriptivi (full-sample e acceptabil — nu pretind
tranzacționare). Doar **E** afirmă „echipa funcționează", și o face **exclusiv pe
walk-forward / out-of-sample**, cu z-score cauzal (vezi Capcane). Așa nu ajungem
cu un model care arată grozav doar fiindcă a memorat istoricul.

## Arhitectură

```
cache 15m (NVDA, AAPL, MSFT, AMD, TSLA)   [markov/intraday/cache.py]
  └─ resample → daily (+1h, 15m secundare)  [markov/intraday/bars.py]
       └─ adaptor TIER 1: nume -> callable(Bars)->ndarray 1D  [validation/tier1.py]
            └─ A. IC individual + decay   (Spearman rank, pooled pe simboluri)
            └─ B. corelație → clustere de familii redundante
            └─ C. IC marginal (rezidual după ce scoatem restul)
            └─ D. IC condiționat pe regim (prag Hurst implicit; HMM injectabil)
            └─ E. ansamblu equal-weight z-score (cauzal) → backtest.walk_forward
                  + permutation_test (p-value); variantă complexă DOAR dacă bate baseline OOS
       └─ raport: tabel text + CSV opțional
```

Zero dependențe noi (numpy/pandas + stdlib). Spearman se face cu rank pe numpy
(tipar din `markov/xs_signals.py`). Se refolosesc: `backtest.walk_forward`,
`significance.permutation_test`, `hmm_walkforward.hmm_walk_forward_states`,
`intraday.indicators`, `intraday.bars`, `intraday.cache`.

## Module & semnături

### `markov/validation/tier1.py` — strat de adaptare (corecția #1)
Indicatorii TIER 1 au semnături **heterogene** (OHLC vs close; fără window;
randamente; `jump_component` întoarce tuplu). Adaptorul îi uniformizează:
- `INDICATORS: dict[str, Callable[[Bars], np.ndarray]]` — fiecare întoarce o serie
  1D aliniată la `bars` (NaN pe warmup). `jump_component` e despicat în două
  intrări: `"jump"` și `"jump_ratio"`. `max_effect` primește randamente derivate
  din close. `corwin_schultz` primește high/low. Window-urile au default-uri
  documentate (ex. 20).
- Astfel motorul cunoaște doar „nume → serie", nu argumentele bizare → rămâne
  agnostic. La TIER 2 se adaugă un alt dict, fără a atinge motorul.

### `markov/validation/dataset.py` — materia primă (pur)
- `build_panel(symbols, data_dir, indicators, horizon_tf="1day") -> Panel` — citește
  cache-ul, resample la orizont, calculează seriile de features per simbol,
  aliniate cu randamentele forward. `Panel` = features per simbol + close per
  simbol.
- `forward_returns(close, horizons=(1, 5, 21)) -> dict[int, np.ndarray]` — randament
  la h bare înainte (cu NaN la coadă; ne-suprapus cu indicatorul → fără look-ahead).

### `markov/validation/ic.py` — pașii A, B, C (pur)
- `spearman_ic(signal, fwd_ret) -> float` — IC rank (argsort numpy, fără scipy;
  ignoră NaN-urile aliniat).
- `ic_decay(signal, returns_by_h) -> dict[int, float]` — IC pe fiecare orizont.
- `pooled_ic(per_symbol_ics) -> dict` — `mean`, `std`, `n` peste simboluri.
- `correlation_matrix(features) -> (names, np.ndarray)`.
- `cluster_families(names, corr, thr=0.7) -> list[list[str]]` — grupează redundanții
  (corelație abs ≥ prag).
- `marginal_ic(features, fwd_ret) -> dict[str, float]` — IC al rezidualului fiecărui
  indicator după regresie liniară pe ceilalți (cât adaugă peste echipă).

### `markov/validation/regime.py` — pasul D (pur)
- `hurst_regime(close, window) -> np.ndarray` — etichete `{"trend","meanrev"}` din
  pragul Hurst ≷ 0.5 (implicit; ieftin, fără warmup mare).
- `conditional_ic(signal, fwd_ret, regime_labels) -> dict[str, float]` — IC split pe
  stări. Etichetele sunt **injectabile** — se poate da în loc ieșirea
  `hmm_walk_forward_states` când seria e destul de lungă (warmup=250).

### `markov/validation/ensemble.py` — pasul E (pur; rulează prin walk_forward)
- `zscore_causal(x) -> np.ndarray` — standardizare **expandabilă (doar trecut)**,
  ca să evite look-ahead-ul (corecția #2).
- `equal_weight_signal(features, causal=True) -> np.ndarray` — z-score fiecare +
  medie; `causal=False` doar pentru afișare descriptivă.
- `evaluate_ensemble(features, prices, regime_labels=None) -> EnsembleReport` —
  construiește semnalul cauzal → `walk_forward` (Sharpe/IC OOS, cost configurabil)
  + `permutation_test` (p-value). Dacă primește și un model fitat, îl compară cu
  baseline-ul și marchează `complexity_justified: bool` (bate OOS sau nu).

### `markov/validation/report.py` — agregare + ieșire (pur)
- `ValidationReport` dataclass (rezultatele A–E).
- `render_text() -> str` — tabel ca `markov/dashboard.py`; fiecare ieșire poartă
  „NU este consiliere de investiții".
- `to_csv(path)` — opțional.

### `validate_cli.py` (rădăcină) — orchestrare + CLI
- `argparse`: `--symbols --data-dir --horizons --indicators tier1 --out report.csv`.
- Cablează `validation.tier1.INDICATORS` ca primul client; rulează A→E; tipărește
  raportul. Tipar din `telegram_alert.py`.

## Capcane abordate (corecțiile din verificarea semnăturilor)

1. **Semnături heterogene** → strat de adaptare `tier1.py` (mai sus).
2. **Look-ahead în z-score**: `walk_forward` arată doar trecutul; standardizarea
   pe toată seria ar fi furat din viitor. → `zscore_causal` expandabil în pasul E;
   full-sample doar la afișarea descriptivă A–D.
3. **Orizonturi & regim**: pe daily `(1,5,21)` (nu `(1,4,21)`, care era intraday);
   regim implicit = prag Hurst (HMM cere warmup 250 ≈ tot anul de date → opțional).

## Plan de testare (TDD, `tests/test_validation_*.py`)

- **tier1:** fiecare cheie din `INDICATORS` întoarce o serie de lungimea barelor;
  `jump`/`jump_ratio` separate; nicio cheie nu aruncă pe un `Bars` mic valid.
- **dataset:** `forward_returns` cu serie cunoscută (h=1,5,21) → valori și NaN la
  coadă corecte; `build_panel` aliniază features și randamente, fără look-ahead.
- **ic:** `spearman_ic` = +1 pe monoton crescător, −1 pe descrescător, ~0 pe
  zgomot; `pooled_ic` mediere + std corecte; `cluster_families` grupează doi
  indicatori identici; `marginal_ic` al unui duplicat ≈ 0 (nu adaugă nimic).
- **regime:** `hurst_regime` etichetează trend vs mean-revert pe serii sintetice;
  `conditional_ic` separă corect pe etichete cunoscute.
- **ensemble:** `zscore_causal` nu folosește viitorul (valoarea la t nu se schimbă
  dacă modifici x[t+1:]); `equal_weight_signal` mediere corectă; `evaluate_ensemble`
  pe semnal sintetic predictiv → Sharpe>0 & p_value mic; pe zgomot → p_value mare.
- **report:** `render_text` conține disclaimerul și toate secțiunile A–E.
- **cli (smoke):** pe cache pre-seedat, rulează A→E și produce raport ne-gol.

## Verificare

1. **Offline:** `python -m pytest -q` → tot verde (funcții pure + smoke CLI pe cache
   pre-seedat). Confirmă A–E fără rețea.
2. **Pe date reale (după backfill AV):** `python validate_cli.py --indicators tier1
   --symbols NVDA,AAPL,MSFT,AMD,TSLA` → raportul real; interpretăm împreună ce
   indicatori au IC marginal real și dacă ansamblul bate baseline-ul OOS.

## Ce NU e în v1 (YAGNI)

- Selecție automată de model / hyperparametri (doar baseline + o variantă comparată).
- Indicatori TIER 2 (cross-asset) — sub-proiect ulterior; motorul îi va accepta
  prin alt dict `INDICATORS`, fără rescriere.
- Optimizare de portofoliu / execuție — separat.

## Constrângeri de proiect (rămân în vigoare)

- Dezvoltare doar pe `claude/upbeat-fermi-L3dat`; commit-uri clare; fără PR decât la
  cerere.
- Zero dependențe noi.
- Fiecare ieșire poartă „NU este consiliere de investiții".
- Fără secrete hardcodate/logate.
