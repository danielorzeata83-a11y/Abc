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
