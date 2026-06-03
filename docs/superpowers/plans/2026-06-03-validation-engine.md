# Motor de validare indicatori — Plan de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un motor agnostic care ia orice set de indicatori + simboluri și produce un raport de validare (IC individual+decay, corelație/familii, IC marginal, IC pe regim, ansamblu walk-forward), demonstrat pe cei 13 indicatori TIER 1.

**Architecture:** Pachet pur `markov/validation/` (numpy/pandas, zero deps noi) + CLI `validate_cli.py`. Pașii A–D sunt descriptivi (full-sample ok); pasul E pretinde edge → rulează exclusiv cauzal prin `backtest.walk_forward` + `significance.permutation_test`. Indicatorii heterogeni sunt uniformizați printr-un strat de adaptare `tier1.py` (`nume -> callable(Bars)->ndarray`).

**Tech Stack:** numpy, pandas, stdlib; reutilizează `markov/backtest.py`, `markov/significance.py`, `markov/hmm_walkforward.py`, `markov/intraday/{indicators,bars,cache}.py`.

Spec: `docs/superpowers/specs/2026-06-03-validation-engine-design.md`.

---

## Structura fișierelor

- Create: `markov/validation/__init__.py` — docstring pachet.
- Create: `markov/validation/ic.py` — Spearman IC, decay, pooled, corelație, familii, IC marginal (pașii A,B,C).
- Create: `markov/validation/ensemble.py` — z-score cauzal, equal-weight, evaluare walk-forward (pasul E).
- Create: `markov/validation/regime.py` — etichete de regim + IC condiționat (pasul D).
- Create: `markov/validation/dataset.py` — `forward_returns`, `Panel`, `build_panel`.
- Create: `markov/validation/tier1.py` — adaptoare `INDICATORS` pentru cei 13 TIER 1.
- Create: `markov/validation/report.py` — `ValidationReport`, `render_text`, `to_csv`.
- Create: `validate_cli.py` — orchestrare A→E + argparse.
- Create: `tests/test_validation_{ic,ensemble,regime,dataset,tier1,report,cli}.py`.

Fiecare fișier o singură responsabilitate; funcții pure, ușor de testat izolat.

---

## Task 1: `ic.py` — Spearman IC, decay, pooled (pasul A)

**Files:**
- Create: `markov/validation/__init__.py`
- Create: `markov/validation/ic.py`
- Test: `tests/test_validation_ic.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_ic.py
import numpy as np
from markov.validation import ic


def test_spearman_ic_monotonic():
    x = np.arange(20.0)
    assert ic.spearman_ic(x, x) > 0.999
    assert ic.spearman_ic(x, -x) < -0.999


def test_spearman_ic_ignores_nan_and_noise():
    rng = np.random.default_rng(0)
    s = rng.normal(size=300); r = rng.normal(size=300)
    val = ic.spearman_ic(s, r)
    assert abs(val) < 0.2          # noise -> ~0
    s2 = s.copy(); s2[:5] = np.nan
    assert np.isfinite(ic.spearman_ic(s2, r))   # NaN rows dropped, still finite


def test_ic_decay_per_horizon():
    x = np.arange(50.0)
    returns_by_h = {1: x, 5: -x}
    d = ic.ic_decay(x, returns_by_h)
    assert d[1] > 0.99 and d[5] < -0.99


def test_pooled_ic_mean_std():
    out = ic.pooled_ic([0.1, 0.2, np.nan, 0.3])
    assert abs(out["mean"] - 0.2) < 1e-9
    assert out["n"] == 3
    assert out["std"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_ic.py -q`
Expected: FAIL (module `markov.validation` not found).

- [ ] **Step 3: Write minimal implementation**

```python
# markov/validation/__init__.py
"""Motor de validare a indicatorilor (agnostic). NU este consiliere de investitii."""
```

```python
# markov/validation/ic.py
"""Information Coefficient: Spearman rank IC, decay pe orizonturi, pooled pe simboluri.

Functii pure pe array-uri numpy. Spearman = Pearson pe ranguri (fara scipy),
in stilul markov/xs_signals.py. NaN-urile se mascheaza aliniat inainte de calcul.
"""

import numpy as np


def _rankdata(a):
    """Ranguri medii (1..n), ca scipy.stats.rankdata fara dependinta."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)
    # medie pe legaturi
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts)); np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def spearman_ic(signal, fwd_ret):
    """IC rank intre signal_t si randamentul forward. NaN-safe; nan daca <3 puncte."""
    s = np.asarray(signal, dtype=float)
    r = np.asarray(fwd_ret, dtype=float)
    m = np.isfinite(s) & np.isfinite(r)
    if m.sum() < 3:
        return float("nan")
    rs, rr = _rankdata(s[m]), _rankdata(r[m])
    if rs.std() == 0 or rr.std() == 0:
        return float("nan")
    return float(np.corrcoef(rs, rr)[0, 1])


def ic_decay(signal, returns_by_h):
    """{h: IC} pentru fiecare orizont din dict-ul returns_by_h."""
    return {h: spearman_ic(signal, ret) for h, ret in returns_by_h.items()}


def pooled_ic(per_symbol_ics):
    """Agrega IC-uri per simbol: mean/std/n peste valorile finite."""
    arr = np.asarray([v for v in per_symbol_ics], dtype=float)
    fin = arr[np.isfinite(arr)]
    if len(fin) == 0:
        return {"mean": float("nan"), "std": float("nan"), "n": 0}
    return {"mean": float(fin.mean()),
            "std": float(fin.std(ddof=0)),
            "n": int(len(fin))}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_ic.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/__init__.py markov/validation/ic.py tests/test_validation_ic.py
git commit -m "feat(validation): Spearman IC, decay, pooled (pasul A)"
```

---

## Task 2: `ic.py` — corelație, familii, IC marginal (pașii B, C)

**Files:**
- Modify: `markov/validation/ic.py` (adaugă 3 funcții)
- Test: `tests/test_validation_ic.py` (adaugă teste)

- [ ] **Step 1: Write the failing test**

```python
# adauga in tests/test_validation_ic.py
def test_correlation_and_families():
    x = np.arange(40.0)
    feats = {"a": x, "b": 2 * x + 1, "c": np.sin(x)}   # a,b colineare
    names, corr = ic.correlation_matrix(feats)
    i, j = names.index("a"), names.index("b")
    assert corr[i, j] > 0.99
    fams = ic.cluster_families(names, corr, thr=0.9)
    assert any({"a", "b"} <= set(f) for f in fams)     # a,b in aceeasi familie


def test_marginal_ic_of_duplicate_is_zero():
    rng = np.random.default_rng(1)
    base = rng.normal(size=200)
    fwd = base + rng.normal(size=200) * 0.1
    feats = {"x": base, "x_copy": base.copy()}         # x_copy nu adauga nimic
    marg = ic.marginal_ic(feats, fwd)
    assert abs(marg["x_copy"]) < 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_ic.py -q`
Expected: FAIL (`correlation_matrix` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# adauga in markov/validation/ic.py
def correlation_matrix(features):
    """(names, matrice Pearson) pe perechile cu suprapunere finita."""
    names = list(features.keys())
    cols = [np.asarray(features[n], dtype=float) for n in names]
    k = len(names)
    corr = np.eye(k)
    for i in range(k):
        for j in range(i + 1, k):
            m = np.isfinite(cols[i]) & np.isfinite(cols[j])
            if m.sum() >= 3 and cols[i][m].std() > 0 and cols[j][m].std() > 0:
                c = float(np.corrcoef(cols[i][m], cols[j][m])[0, 1])
            else:
                c = float("nan")
            corr[i, j] = corr[j, i] = c
    return names, corr


def cluster_families(names, corr, thr=0.7):
    """Grupeaza indicatorii cu |corelatie| >= thr (union-find simplu)."""
    parent = list(range(len(names)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if np.isfinite(corr[i, j]) and abs(corr[i, j]) >= thr:
                parent[find(i)] = find(j)
    groups = {}
    for idx, name in enumerate(names):
        groups.setdefault(find(idx), []).append(name)
    return list(groups.values())


def marginal_ic(features, fwd_ret):
    """Pentru fiecare indicator: IC al rezidualului dupa regresie liniara pe ceilalti.

    Masoara cat adauga indicatorul PESTE restul echipei (ortogonalitate).
    Aliniaza pe randurile finite comune tuturor feature-urilor + fwd_ret.
    """
    names = list(features.keys())
    cols = [np.asarray(features[n], dtype=float) for n in names]
    r = np.asarray(fwd_ret, dtype=float)
    mask = np.isfinite(r)
    for c in cols:
        mask &= np.isfinite(c)
    out = {}
    if mask.sum() < 5:
        return {n: float("nan") for n in names}
    X = np.column_stack([c[mask] for c in cols])
    rr = r[mask]
    for idx, name in enumerate(names):
        y = X[:, idx]
        others = np.delete(X, idx, axis=1)
        if others.shape[1] == 0:
            resid = y - y.mean()
        else:
            A = np.column_stack([others, np.ones(len(y))])
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
            resid = y - A @ coef
        out[name] = spearman_ic(resid, rr)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_ic.py -q`
Expected: PASS (6 tests total).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/ic.py tests/test_validation_ic.py
git commit -m "feat(validation): corelatie, familii, IC marginal (pasii B,C)"
```

---

## Task 3: `ensemble.py` — z-score cauzal + equal-weight

**Files:**
- Create: `markov/validation/ensemble.py`
- Test: `tests/test_validation_ensemble.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_ensemble.py
import numpy as np
from markov.validation import ensemble


def test_zscore_causal_no_lookahead():
    rng = np.random.default_rng(0)
    x = rng.normal(size=50)
    z = ensemble.zscore_causal(x)
    # modificarea viitorului nu schimba valoarea la t=20
    x2 = x.copy(); x2[30:] += 100.0
    z2 = ensemble.zscore_causal(x2)
    assert abs(z[20] - z2[20]) < 1e-9


def test_equal_weight_is_mean_of_zscores():
    x = np.arange(30.0)
    feats = {"a": x, "b": x}
    sig = ensemble.equal_weight_signal(feats, causal=False)
    za = (x - x.mean()) / x.std()
    assert np.allclose(sig[5:], za[5:], atol=1e-9)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_ensemble.py -q`
Expected: FAIL (`zscore_causal` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# markov/validation/ensemble.py
"""Ansamblu de indicatori (pasul E). Z-score CAUZAL (doar trecut) pentru a evita
look-ahead-ul; full-sample doar pentru afisare descriptiva. Evaluarea ruleaza prin
backtest.walk_forward + significance.permutation_test. NU este consiliere de investitii.
"""

import numpy as np


def zscore_causal(x):
    """Standardizare expandabila: z[t] = (x[t]-mean(x[:t+1]))/std(x[:t+1]).

    Foloseste DOAR trecutul (inclusiv t). nan unde <2 puncte finite sau std==0.
    """
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    for t in range(len(x)):
        past = x[: t + 1]
        fin = past[np.isfinite(past)]
        if len(fin) >= 2 and fin.std(ddof=0) > 0:
            out[t] = (x[t] - fin.mean()) / fin.std(ddof=0)
    return out


def _zscore_full(x):
    x = np.asarray(x, dtype=float)
    fin = x[np.isfinite(x)]
    if len(fin) < 2 or fin.std(ddof=0) == 0:
        return np.full(len(x), np.nan)
    return (x - fin.mean()) / fin.std(ddof=0)


def equal_weight_signal(features, causal=True):
    """Media (nanmean) z-score-urilor indicatorilor -> un singur semnal aliniat."""
    fn = zscore_causal if causal else _zscore_full
    zs = np.column_stack([fn(np.asarray(v, dtype=float)) for v in features.values()])
    with np.errstate(invalid="ignore"):
        return np.nanmean(zs, axis=1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_ensemble.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/ensemble.py tests/test_validation_ensemble.py
git commit -m "feat(validation): z-score cauzal + equal-weight signal"
```

---

## Task 4: `ensemble.py` — `evaluate_ensemble` (walk-forward + permutation)

**Files:**
- Modify: `markov/validation/ensemble.py`
- Test: `tests/test_validation_ensemble.py`

- [ ] **Step 1: Write the failing test**

```python
# adauga in tests/test_validation_ensemble.py
def test_evaluate_ensemble_detects_real_signal():
    rng = np.random.default_rng(3)
    n = 400
    rets = rng.normal(0, 0.01, size=n)
    prices = 100 * np.cumprod(1 + rets)
    # feature care "stie" randamentul de maine (semnal real, deplasat ca sa fie cauzal)
    look = np.empty(n); look[:-1] = rets[1:]; look[-1] = 0.0
    feats = {"oracle": look}
    res = ensemble.evaluate_ensemble(feats, prices, warmup=20)
    assert res["net_return"] > 0
    assert res["p_value"] < 0.05


def test_evaluate_ensemble_noise_not_significant():
    rng = np.random.default_rng(4)
    n = 400
    prices = 100 * np.cumprod(1 + rng.normal(0, 0.01, size=n))
    feats = {"noise": rng.normal(size=n)}
    res = ensemble.evaluate_ensemble(feats, prices, warmup=20)
    assert res["p_value"] > 0.05
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_ensemble.py::test_evaluate_ensemble_detects_real_signal -q`
Expected: FAIL (`evaluate_ensemble` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# adauga in markov/validation/ensemble.py (sus, langa import numpy)
from markov.backtest import walk_forward
from markov.significance import permutation_test


def evaluate_ensemble(features, prices, warmup=20, cost=0.0, n_perm=1000, seed=0):
    """Construieste semnalul cauzal -> strategie walk-forward -> metrici OOS.

    Pozitia in ziua t = tanh(semnal_equal_weight_cauzal[t]), folosind doar trecutul.
    Returneaza net_return, sharpe (anualizat ~252), p_value (permutation test),
    si n_days. NU este consiliere de investitii.
    """
    prices = np.asarray(prices, dtype=float)
    signal = equal_weight_signal(features, causal=True)
    position = np.tanh(signal)               # mapeaza in (-1, 1)
    position = np.where(np.isfinite(position), position, 0.0)

    def strategy(past):
        t = len(past) - 1                    # walk_forward da prices[:t+1]
        return position[t]

    res = walk_forward(prices, strategy, warmup=warmup, cost=cost)

    n = len(prices)
    # randamente forward aliniate cu pozitiile (t = warmup .. n-2)
    fwd = prices[warmup + 1:n] / prices[warmup:n - 1] - 1.0
    pos = res["positions"]
    daily = pos * fwd
    sharpe = float(daily.mean() / daily.std(ddof=0) * np.sqrt(252)) \
        if daily.std(ddof=0) > 0 else 0.0
    perm = permutation_test(pos, fwd, n_perm=n_perm, seed=seed)
    return {
        "net_return": res["net_return"],
        "sharpe": sharpe,
        "p_value": perm["p_value"],
        "n_days": res["n_days"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_ensemble.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/ensemble.py tests/test_validation_ensemble.py
git commit -m "feat(validation): evaluate_ensemble walk-forward + permutation"
```

---

## Task 5: `regime.py` — etichete Hurst + IC condiționat (pasul D)

**Files:**
- Create: `markov/validation/regime.py`
- Test: `tests/test_validation_regime.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_regime.py
import numpy as np
from markov.validation import regime


def test_hurst_regime_labels_trend_vs_meanrev():
    rng = np.random.default_rng(0)
    trend = np.cumsum(np.abs(rng.normal(1.0, 0.1, size=300)))   # H>0.5
    labels = regime.hurst_regime(trend, window=100)
    tail = labels[150:]
    assert (tail == "trend").sum() > (tail == "meanrev").sum()


def test_conditional_ic_splits_by_regime():
    sig = np.array([1.0, 2, 3, 4, 5, 6])
    fwd = np.array([1.0, 2, 3, -4, -5, -6])
    labels = np.array(["a", "a", "a", "b", "b", "b"])
    d = regime.conditional_ic(sig, fwd, labels)
    assert d["a"] > 0.99 and d["b"] < -0.99
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_regime.py -q`
Expected: FAIL (`hurst_regime` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# markov/validation/regime.py
"""Pasul D: IC condiționat pe regim. Eticheta implicita = prag Hurst (≷0.5);
etichetele sunt INJECTABILE (poti da iesirea hmm_walk_forward_states cand seria
e destul de lunga). NU este consiliere de investitii.
"""

import numpy as np

from markov.intraday.indicators import hurst
from markov.validation.ic import spearman_ic


def hurst_regime(close, window=100):
    """Etichete: 'trend' unde Hurst>0.5, 'meanrev' unde <0.5, 'na' unde NaN."""
    h = hurst(np.asarray(close, dtype=float), window)
    labels = np.full(len(h), "na", dtype=object)
    labels[h > 0.5] = "trend"
    labels[(h <= 0.5) & np.isfinite(h)] = "meanrev"
    return labels


def conditional_ic(signal, fwd_ret, regime_labels):
    """{regim: IC} calculat pe submultimea fiecarui regim ('na' ignorat)."""
    signal = np.asarray(signal, dtype=float)
    fwd_ret = np.asarray(fwd_ret, dtype=float)
    labels = np.asarray(regime_labels, dtype=object)
    out = {}
    for reg in sorted(set(labels.tolist())):
        if reg == "na":
            continue
        m = labels == reg
        out[reg] = spearman_ic(signal[m], fwd_ret[m])
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_regime.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/regime.py tests/test_validation_regime.py
git commit -m "feat(validation): regim Hurst + IC conditionat (pasul D)"
```

---

## Task 6: `dataset.py` — `forward_returns`

**Files:**
- Create: `markov/validation/dataset.py`
- Test: `tests/test_validation_dataset.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_dataset.py
import numpy as np
from markov.validation import dataset


def test_forward_returns_horizons_and_tail_nan():
    close = np.array([100.0, 110, 121, 133.1])     # +10% pe pas
    out = dataset.forward_returns(close, horizons=(1, 2))
    assert np.isclose(out[1][0], 0.10)
    assert np.isnan(out[1][-1])                     # ultimul nu are h=1 inainte
    assert np.isclose(out[2][0], 0.21)
    assert np.isnan(out[2][-1]) and np.isnan(out[2][-2])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_dataset.py -q`
Expected: FAIL (`forward_returns` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# markov/validation/dataset.py
"""Materia prima pentru validare: randamente forward + panel multi-simbol.
Functii pure peste cache-ul 15m (resample la orizont). NU consiliere de investitii.
"""

from dataclasses import dataclass

import numpy as np

from markov.data_providers import DataUnavailable
from markov.intraday.bars import resample
from markov.intraday.cache import read_bars


def forward_returns(close, horizons=(1, 5, 21)):
    """{h: randament la h bare inainte}; nan pentru ultimele h pozitii."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = {}
    for h in horizons:
        r = np.full(n, np.nan)
        if h < n:
            r[: n - h] = close[h:] / close[: n - h] - 1.0
        out[h] = r
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_dataset.py -q`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/dataset.py tests/test_validation_dataset.py
git commit -m "feat(validation): forward_returns multi-orizont"
```

---

## Task 7: `tier1.py` — adaptoare uniforme pentru cei 13 indicatori

**Files:**
- Create: `markov/validation/tier1.py`
- Test: `tests/test_validation_tier1.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_tier1.py
import numpy as np
from markov.intraday.bars import Bars
from markov.validation import tier1


def _bars(n=260):
    rng = np.random.default_rng(0)
    ts = np.arange(n).astype("datetime64[D]")
    close = 100 + np.cumsum(rng.normal(0, 1, size=n))
    o = close + rng.normal(0, 0.1, size=n)
    h = np.maximum(o, close) + np.abs(rng.normal(0, 0.2, size=n))
    l = np.minimum(o, close) - np.abs(rng.normal(0, 0.2, size=n))
    v = np.abs(rng.normal(1e6, 1e5, size=n))
    return Bars(ts, o, h, l, close, v)


def test_indicators_dict_has_expected_keys():
    assert "jump" in tier1.INDICATORS and "jump_ratio" in tier1.INDICATORS
    assert len(tier1.INDICATORS) >= 14          # 13 indicatori, jump despicat in 2


def test_every_adapter_returns_aligned_series():
    b = _bars()
    for name, fn in tier1.INDICATORS.items():
        out = fn(b)
        assert isinstance(out, np.ndarray), name
        assert len(out) == len(b), name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_tier1.py -q`
Expected: FAIL (`tier1` not found).

- [ ] **Step 3: Write minimal implementation**

```python
# markov/validation/tier1.py
"""Strat de adaptare: uniformizeaza cei 13 indicatori TIER 1 (semnaturi heterogene)
intr-un dict `nume -> callable(Bars) -> ndarray 1D` aliniat la bare. jump_component
e despicat in 'jump' si 'jump_ratio'. Default-uri potrivite pentru daily.
Motorul ramane agnostic: cunoaste doar 'nume -> serie'. NU consiliere de investitii.
"""

import numpy as np

from markov.intraday import indicators as I

# Default-uri (daily): ferestre scurte pentru vol/complexitate, mai lungi pt memorie.
_W = 20            # fereastra vol / lichiditate / entropie
_W_HURST = 100     # Hurst/FDI au nevoie de istoric mai lung
_W_RQA = 100       # rqa: window <= 200
_LOOKBACK_52W = 126  # ~6 luni (1 an de daily ar lasa o singura valoare ne-NaN)
_W_MAX = 21        # MAX effect pe ~o luna


def _ret(bars):
    c = np.asarray(bars.close, dtype=float)
    r = np.full(len(c), np.nan)
    r[1:] = c[1:] / c[:-1] - 1.0
    return r


def _rqa_eps(bars):
    c = np.asarray(bars.close, dtype=float)
    s = np.nanstd(c)
    return 0.1 * s if s > 0 else 1e-6


INDICATORS = {
    "garman_klass":    lambda b: I.garman_klass(b.open, b.high, b.low, b.close, _W),
    "rogers_satchell": lambda b: I.rogers_satchell(b.open, b.high, b.low, b.close, _W),
    "realized_var":    lambda b: I.realized_variance(b.close, _W),
    "bipower_var":     lambda b: I.bipower_variation(b.close, _W),
    "jump":            lambda b: I.jump_component(b.close, _W)[0],
    "jump_ratio":      lambda b: I.jump_component(b.close, _W)[1],
    "hurst":           lambda b: I.hurst(b.close, _W_HURST),
    "fdi":             lambda b: I.fdi(b.close, _W_HURST),
    "perm_entropy":    lambda b: I.permutation_entropy(b.close, 3, _W),
    "rqa_det":         lambda b: I.rqa_determinism(b.close, _W_RQA, _rqa_eps(b)),
    "corwin_schultz":  lambda b: I.corwin_schultz(b.high, b.low),
    "roll_measure":    lambda b: I.roll_measure(b.close, _W),
    "high_52w_prox":   lambda b: I.high_52w_proximity(b.close, _LOOKBACK_52W),
    "max_effect":      lambda b: I.max_effect(_ret(b), _W_MAX),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_tier1.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/tier1.py tests/test_validation_tier1.py
git commit -m "feat(validation): adaptoare uniforme pentru cei 13 indicatori TIER 1"
```

---

## Task 8: `dataset.py` — `Panel` + `build_panel`

**Files:**
- Modify: `markov/validation/dataset.py`
- Test: `tests/test_validation_dataset.py`

- [ ] **Step 1: Write the failing test**

```python
# adauga in tests/test_validation_dataset.py
import pandas as pd
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import tier1


def _seed(dirpath, symbol, n=300):
    idx = pd.date_range("2025-01-02 09:30", periods=n, freq="15min")
    rng = np.random.default_rng(1)
    close = 100 + np.cumsum(rng.normal(0, 0.2, size=n))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_build_panel_aligns_features_and_returns(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    panel = dataset.build_panel(["AAA", "BBB"], d, tier1.INDICATORS,
                                horizon_tf="1day", horizons=(1, 5))
    assert set(panel.symbols) == {"AAA", "BBB"}
    feats = panel.features["AAA"]
    assert "hurst" in feats
    nbars = len(panel.close["AAA"])
    assert len(feats["hurst"]) == nbars
    assert len(panel.returns["AAA"][1]) == nbars


def test_build_panel_missing_symbol_raises(tmp_path):
    import pytest
    with pytest.raises(dataset.DataUnavailable):
        dataset.build_panel(["NOPE"], str(tmp_path), tier1.INDICATORS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_dataset.py -q`
Expected: FAIL (`build_panel` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# adauga in markov/validation/dataset.py
@dataclass
class Panel:
    symbols: list
    features: dict   # symbol -> {indicator_name: ndarray}
    close: dict      # symbol -> ndarray
    returns: dict    # symbol -> {h: ndarray}


def build_panel(symbols, data_dir, indicators, horizon_tf="1day",
                horizons=(1, 5, 21)):
    """Citeste cache-ul 15m, resample la horizon_tf, calculeaza features + randamente
    forward per simbol. Ridica DataUnavailable daca un simbol nu e in cache."""
    features, close, returns = {}, {}, {}
    for sym in symbols:
        bars15 = read_bars(data_dir, sym)
        if bars15 is None:
            raise DataUnavailable(f"fara cache pentru {sym}")
        bars = resample(bars15, horizon_tf) if horizon_tf != "15m" else bars15
        c = np.asarray(bars.close, dtype=float)
        features[sym] = {name: np.asarray(fn(bars), dtype=float)
                         for name, fn in indicators.items()}
        close[sym] = c
        returns[sym] = forward_returns(c, horizons=horizons)
    return Panel(list(symbols), features, close, returns)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_dataset.py -q`
Expected: PASS (3 tests total).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/dataset.py tests/test_validation_dataset.py
git commit -m "feat(validation): Panel + build_panel multi-simbol"
```

---

## Task 9: `report.py` — agregare A→E + ieșire

**Files:**
- Create: `markov/validation/report.py`
- Test: `tests/test_validation_report.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_report.py
import numpy as np
import pandas as pd
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import tier1, report


def _seed(dirpath, symbol, n=320):
    idx = pd.date_range("2025-01-02 09:30", periods=n, freq="15min")
    rng = np.random.default_rng(2)
    close = 100 + np.cumsum(rng.normal(0, 0.2, size=n))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_run_validation_produces_report(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    rep = report.run_validation(["AAA", "BBB"], d, tier1.INDICATORS,
                                horizons=(1, 5))
    txt = rep.render_text()
    assert "consiliere de investi" in txt.lower()    # disclaimer prezent
    assert "IC" in txt and "ansamblu" in txt.lower()
    assert "hurst" in txt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_report.py -q`
Expected: FAIL (`run_validation` not defined).

- [ ] **Step 3: Write minimal implementation**

```python
# markov/validation/report.py
"""Agrega pasii A-E intr-un ValidationReport + redare text/CSV.
Fiecare iesire poarta disclaimerul. NU este consiliere de investitii.
"""

from dataclasses import dataclass

import numpy as np

from markov.validation import ic, ensemble, regime
from markov.validation.dataset import build_panel

DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare."


@dataclass
class ValidationReport:
    pooled_ic: dict          # indicator -> {h: {mean,std,n}}
    families: list           # list[list[str]]
    marginal: dict           # h -> {indicator: marginal_ic}
    conditional: dict        # indicator -> {regim: IC} (orizont principal)
    ensemble: dict           # rezultat evaluate_ensemble (pooled simboluri)
    horizons: tuple

    def render_text(self):
        L = [DISCLAIMER, "", "=== Validare indicatori (A->E) ===", ""]
        L.append("[A] Pooled IC (mean) pe orizonturi:")
        header = "  " + "indicator".ljust(16) + "".join(f"h={h}".rjust(9)
                                                         for h in self.horizons)
        L.append(header)
        for name in sorted(self.pooled_ic):
            row = "  " + name.ljust(16)
            for h in self.horizons:
                row += f"{self.pooled_ic[name][h]['mean']:+.3f}".rjust(9)
            L.append(row)
        L.append("")
        L.append("[B] Familii (corelate): " +
                 " | ".join("{" + ",".join(f) + "}" for f in self.families))
        L.append("")
        h0 = self.horizons[0]
        L.append(f"[C] IC marginal (h={h0}):")
        for name in sorted(self.marginal[h0]):
            L.append(f"  {name.ljust(16)}{self.marginal[h0][name]:+.3f}")
        L.append("")
        L.append("[D] IC conditionat pe regim (primul indicator, h=%d):" % h0)
        for name in sorted(self.conditional):
            parts = " ".join(f"{r}={v:+.3f}" for r, v in self.conditional[name].items())
            L.append(f"  {name.ljust(16)}{parts}")
        L.append("")
        e = self.ensemble
        L.append("[E] Ansamblu equal-weight (walk-forward, pooled simboluri):")
        L.append(f"  net_return={e['net_return']:+.3f}  sharpe={e['sharpe']:+.2f}"
                 f"  p_value={e['p_value']:.3f}  n_days={e['n_days']}")
        L.append("")
        L.append(DISCLAIMER)
        return "\n".join(L)

    def to_csv(self, path):
        import csv
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["# " + DISCLAIMER])
            w.writerow(["indicator"] + [f"pooled_ic_h{h}" for h in self.horizons] +
                       [f"marginal_ic_h{self.horizons[0]}"])
            for name in sorted(self.pooled_ic):
                w.writerow([name] +
                           [self.pooled_ic[name][h]["mean"] for h in self.horizons] +
                           [self.marginal[self.horizons[0]].get(name, "")])


def run_validation(symbols, data_dir, indicators, horizon_tf="1day",
                   horizons=(1, 5, 21)):
    """Ruleaza A->E si intoarce un ValidationReport. Pooled pe simboluri."""
    panel = build_panel(symbols, data_dir, indicators, horizon_tf, horizons)
    names = list(indicators.keys())

    # [A] pooled IC: per indicator, per orizont, mediat peste simboluri
    pooled = {}
    for name in names:
        pooled[name] = {}
        for h in horizons:
            ics = [ic.spearman_ic(panel.features[s][name], panel.returns[s][h])
                   for s in symbols]
            pooled[name][h] = ic.pooled_ic(ics)

    # [B] familii: corelatie pe features concatenate peste simboluri
    concat = {name: np.concatenate([panel.features[s][name] for s in symbols])
              for name in names}
    cnames, corr = ic.correlation_matrix(concat)
    families = ic.cluster_families(cnames, corr, thr=0.7)

    # [C] IC marginal per orizont, pe features concatenate
    marginal = {}
    for h in horizons:
        fwd = np.concatenate([panel.returns[s][h] for s in symbols])
        marginal[h] = ic.marginal_ic(concat, fwd)

    # [D] IC conditionat pe regim (orizont principal), per indicator, pooled
    h0 = horizons[0]
    conditional = {}
    for name in names:
        accum = {}
        for s in symbols:
            labels = regime.hurst_regime(panel.close[s])
            cic = regime.conditional_ic(panel.features[s][name],
                                        panel.returns[s][h0], labels)
            for r, v in cic.items():
                accum.setdefault(r, []).append(v)
        conditional[name] = {r: ic.pooled_ic(vs)["mean"] for r, vs in accum.items()}

    # [E] ansamblu equal-weight walk-forward, pooled (mediaza metricile peste simboluri)
    metrics = []
    for s in symbols:
        metrics.append(ensemble.evaluate_ensemble(panel.features[s], panel.close[s]))
    ens = {k: float(np.mean([m[k] for m in metrics]))
           for k in ("net_return", "sharpe", "p_value", "n_days")}

    return ValidationReport(pooled, families, marginal, conditional, ens,
                            tuple(horizons))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_report.py -q`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add markov/validation/report.py tests/test_validation_report.py
git commit -m "feat(validation): run_validation A->E + raport text/CSV"
```

---

## Task 10: `validate_cli.py` — CLI + smoke

**Files:**
- Create: `validate_cli.py`
- Test: `tests/test_validation_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_cli.py
import numpy as np
import pandas as pd
from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
import validate_cli


def _seed(dirpath, symbol, n=320):
    idx = pd.date_range("2025-01-02 09:30", periods=n, freq="15min")
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 0.2, size=n))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_cli_runs_and_prints_report(tmp_path, capsys):
    d = str(tmp_path)
    _seed(d, "AAA"); _seed(d, "BBB")
    validate_cli.main(["--symbols", "AAA,BBB", "--data-dir", d,
                       "--horizons", "1,5"])
    out = capsys.readouterr().out
    assert "consiliere de investi" in out.lower()
    assert "Ansamblu" in out or "ansamblu" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation_cli.py -q`
Expected: FAIL (`validate_cli` not found).

- [ ] **Step 3: Write minimal implementation**

```python
# validate_cli.py
"""CLI: ruleaza motorul de validare pe cei 13 indicatori TIER 1.

    python validate_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday

Citeste cache-ul 15m existent (vezi intraday_server.py pentru backfill).
NU este consiliere de investitii.
"""

import argparse

from markov.validation import tier1
from markov.validation.report import run_validation
from markov.intraday.service import Config


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validare indicatori (A->E).")
    ap.add_argument("--symbols", help="lista simboluri separate prin virgula")
    ap.add_argument("--data-dir")
    ap.add_argument("--horizons", default="1,5,21",
                    help="orizonturi forward in bare (daily)")
    ap.add_argument("--indicators", default="tier1", choices=["tier1"])
    ap.add_argument("--out", help="scrie si CSV la calea data")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else list(cfg.watchlist))
    data_dir = args.data_dir or cfg.data_dir
    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())

    rep = run_validation(symbols, data_dir, tier1.INDICATORS, horizons=horizons)
    print(rep.render_text())
    if args.out:
        rep.to_csv(args.out)
        print(f"\nCSV scris in {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validation_cli.py -q`
Expected: PASS (1 test).

- [ ] **Step 5: Run the full suite + commit**

```bash
python -m pytest -q
git add validate_cli.py tests/test_validation_cli.py
git commit -m "feat(validation): CLI validate_cli pe TIER 1 + smoke"
```

---

## Self-Review (autorul planului)

**Spec coverage:** A→`ic.spearman_ic/ic_decay/pooled_ic`+report[A] (T1,T9); B→`correlation_matrix/cluster_families`+report[B] (T2,T9); C→`marginal_ic`+report[C] (T2,T9); D→`regime`+report[D] (T5,T9); E→`evaluate_ensemble`+report[E] (T3,T4,T9). Strat adaptare heterogen→`tier1.py` (T7). Look-ahead→`zscore_causal` (T3). Orizonturi (1,5,21)→`forward_returns` (T6). Pooled multi-simbol→`build_panel`+`run_validation` (T8,T9). CLI→T10. Disclaimer→`report.py`/CLI. Toate acoperite.

**Placeholder scan:** fără TBD/TODO; fiecare pas de cod are cod complet.

**Type consistency:** `Bars` (timestamps,open,high,low,close,volume); `walk_forward(prices,strategy,warmup,cost)`→dict cu `positions/net_return/n_days` (folosite în T4); `permutation_test(positions,returns)`→`p_value` (T4); `read_bars(data_dir,symbol)`→`Bars|None` (T8); `resample(bars,tf)` (T8); semnăturile indicatorilor din `markov/intraday/indicators.py` se potrivesc cu adaptoarele (T7). `run_validation(...)`→`ValidationReport.render_text/to_csv` (T9,T10). Consistent.

## Constrângeri proiect
- Branch `claude/upbeat-fermi-L3dat`; commit-uri ca `Claude <noreply@anthropic.com>`; fără PR; fiecare commit se termină cu linia de sesiune.
