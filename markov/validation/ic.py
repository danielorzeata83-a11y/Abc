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
    all_names = list(features.keys())
    out = {n: float("nan") for n in all_names}
    # Coloanele prea rare (ex. indicator cu fereastra > istoricul disponibil) nu pot
    # fi nici reziduu, nici variabila de control -> le excludem ca sa nu anuleze, prin
    # complete-case, intreaga sectiune. Indicatorii exclusi raman nan (onest).
    names = [n for n in all_names if np.isfinite(features[n]).sum() >= 5]
    if not names:
        return out
    cols = [np.asarray(features[n], dtype=float) for n in names]
    r = np.asarray(fwd_ret, dtype=float)
    mask = np.isfinite(r)
    for c in cols:
        mask &= np.isfinite(c)
    if mask.sum() < 5:
        return out
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
        scale = np.abs(y).max()
        if scale > 0 and np.abs(resid).max() <= 1e-9 * scale:
            out[name] = 0.0
        else:
            out[name] = spearman_ic(resid, rr)
    return out
