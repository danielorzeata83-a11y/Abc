"""TIER 2b: validarea CROSS-SECTIONALA a familiei de factori pe un univers larg.

low_vol / reversal / momentum / amihud / residual-momentum sunt anomalii
cross-sectionale: edge-ul lor traieste intr-un long-short pe multe active
(cumpara capatul de jos, vinde capatul de sus), NU ca semnal time-series pe
cateva nume corelate (vezi TIER 2). Aici evaluam fiecare factor ca portofoliu:
Sharpe full-sample, Sharpe OUT-OF-SAMPLE si un p-value prin sign-flip pe streamul
de randamente NETE (costurile sunt deja scazute in xs_*_returns).

Univers implicit: data/sp500.csv (panel long, 2013-2018). NU consiliere de investitii.
"""

import numpy as np
import pandas as pd

from markov.amihud import xs_amihud_returns
from markov.lowvol import xs_lowvol_returns
from markov.momentum import xs_momentum_returns
from markov.resmom import xs_residual_momentum_returns
from markov.reversal import xs_reversal_returns

_ANN = np.sqrt(252)
DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare."

FACTORS = {
    "momentum":  lambda P, V: xs_momentum_returns(P),
    "reversal":  lambda P, V: xs_reversal_returns(P),
    "low_vol":   lambda P, V: xs_lowvol_returns(P),
    "resmom":    lambda P, V: xs_residual_momentum_returns(P),
    "amihud":    lambda P, V: xs_amihud_returns(P, V),
}


def load_universe(csv_path):
    """CSV long (date, close, volume, Name) -> (close (T,N), volume (T,N), dates).
    Pastreaza doar numele fara goluri (panel complet) ca sa nu introduca NaN."""
    raw = pd.read_csv(csv_path)
    close = (raw.pivot(index="date", columns="Name", values="close")
                .sort_index().dropna(axis=1))
    cols = close.columns
    volume = (raw.pivot(index="date", columns="Name", values="volume")
                 .sort_index()[cols])
    return (close.to_numpy(dtype=float), volume.to_numpy(dtype=float),
            close.index.to_numpy())


def sharpe(returns):
    """Sharpe anualizat al unui stream de randamente zilnice. nan daca std=0."""
    r = np.asarray(returns, dtype=float)
    s = r.std()
    return float(r.mean() / s * _ANN) if s > 0 and len(r) else float("nan")


def signflip_pvalue(returns, n_perm=2000, seed=0):
    """p one-sided sub nul simetric (semne aleatoare): cat de des media unui
    stream cu semne inversate aleator atinge/depaseste media observata.
    Mic = randamentul mediu pozitiv e improbabil din noroc."""
    r = np.asarray(returns, dtype=float)
    if len(r) == 0:
        return float("nan")
    obs = r.mean()
    rng = np.random.default_rng(seed)
    null = (rng.choice((-1.0, 1.0), size=(n_perm, len(r))) * r).mean(axis=1)
    return float((np.sum(null >= obs) + 1) / (n_perm + 1))


def evaluate_factor(returns, split_frac=0.6, n_perm=2000, seed=0):
    """Sharpe full + OOS + p-value (sign-flip pe segmentul OOS)."""
    r = np.asarray(returns, dtype=float)
    k = int(len(r) * split_frac)
    oos = r[k:]
    return {
        "n_days": len(r),
        "sharpe_full": sharpe(r),
        "sharpe_oos": sharpe(oos),
        "p_value_oos": signflip_pvalue(oos, n_perm=n_perm, seed=seed),
    }


def evaluate_universe(P, V, factors=None, split_frac=0.6, n_perm=2000, seed=0):
    """{nume_factor: metrici} pentru fiecare factor cross-sectional pe panel (P,V)."""
    factors = factors or FACTORS
    return {name: evaluate_factor(fn(P, V), split_frac=split_frac,
                                  n_perm=n_perm, seed=seed)
            for name, fn in factors.items()}


def run_xs_validation(csv_path, factors=None, split_frac=0.6, n_perm=2000, seed=0):
    """Ca evaluate_universe, dar incarca panel-ul dintr-un CSV long."""
    P, V, _dates = load_universe(csv_path)
    return evaluate_universe(P, V, factors=factors, split_frac=split_frac,
                             n_perm=n_perm, seed=seed)


def list_cache_symbols(data_dir):
    """Simbolurile prezente in cache (fisiere {SYMBOL}_15m.csv), sortate."""
    import glob
    import os
    paths = glob.glob(os.path.join(data_dir, "*_15m.csv"))
    return sorted(os.path.basename(p)[:-len("_15m.csv")] for p in paths)


def panel_from_cache(data_dir, symbols=None, horizon_tf="1day"):
    """Construieste panel-ul cross-sectional (P (T,N), V, dates, names) din cache-ul
    daily, pe FEREASTRA COMUNA in care toate numele tranzactioneaza (fara goluri).

    Caveat onest: numai numele care acopera intreaga fereastra comuna supravietuiesc
    (dropna) -> bias de supravietuire daca universul e ales retrospectiv."""
    from markov.intraday.bars import resample
    from markov.intraday.cache import read_bars

    symbols = symbols or list_cache_symbols(data_dir)
    closes, vols = {}, {}
    for s in symbols:
        b = read_bars(data_dir, s)
        if b is None:
            continue
        b = resample(b, horizon_tf) if horizon_tf != "15m" else b
        df = b.to_frame()
        idx = pd.DatetimeIndex(df.index)
        closes[s] = pd.Series(np.asarray(df["close"], dtype=float), index=idx)
        vols[s] = pd.Series(np.asarray(df["volume"], dtype=float), index=idx)
    if len(closes) < 2:
        raise ValueError(f"panel_from_cache: nevoie de >=2 simboluri in cache, gasit {len(closes)}")
    close = pd.DataFrame(closes).sort_index()
    vol = pd.DataFrame(vols).sort_index()
    start = max(close[c].first_valid_index() for c in close.columns)
    end = min(close[c].last_valid_index() for c in close.columns)
    close = close.loc[start:end].dropna(axis=1, how="any").dropna(how="any")
    vol = vol.reindex(close.index)[close.columns]
    return (close.to_numpy(dtype=float), vol.to_numpy(dtype=float),
            close.index.to_numpy(), list(close.columns))


def factor_streams(P, V, factors=None):
    """{nume: stream de randamente} pentru fiecare factor pe panel."""
    factors = factors or FACTORS
    return {name: np.asarray(fn(P, V), dtype=float) for name, fn in factors.items()}


def align_streams(streams):
    """Streamurile xs_*_returns se termina toate in aceeasi zi (T-1) dar incep dupa
    warmup-uri diferite -> sunt RIGHT-aligned. Le taie la coada comuna cea mai scurta.
    Intoarce (names, M) cu M de forma (L, k)."""
    names = list(streams)
    L = min(len(streams[n]) for n in names)
    M = np.column_stack([np.asarray(streams[n], dtype=float)[-L:] for n in names])
    return names, M


def blend_oos(streams, split_frac=0.6, n_perm=2000, seed=0):
    """Blend sign-aware (conviction) al factorilor cross-sectionali, FARA leak:
    ponderile = Sharpe-ul IN-SAMPLE (partea pozitiva, normalizata) ales pe primele
    `split_frac`; factorii care pierd in-sample primesc zero (nu se short-eaza un
    portofoliu dominat de costuri). Evaluat pe segmentul OOS ramas.

    Intoarce ponderi, Sharpe in-sample/OOS si p-value sign-flip pe OOS."""
    names, M = align_streams(streams)
    L, k = M.shape[0], int(M.shape[0] * split_frac)
    ins, oos = M[:k], M[k:]
    sh_in = np.array([sharpe(ins[:, i]) for i in range(M.shape[1])])
    w = np.where(np.isfinite(sh_in) & (sh_in > 0), sh_in, 0.0)
    total = w.sum()
    if total > 0:
        w = w / total
        blended = oos @ w
    else:
        w = np.zeros_like(w)
        blended = np.zeros(oos.shape[0])
    return {
        "weights": dict(zip(names, w)),
        "sharpe_in": dict(zip(names, sh_in)),
        "sharpe_oos": sharpe(blended),
        "p_value_oos": signflip_pvalue(blended, n_perm=n_perm, seed=seed),
        "n_days_oos": len(blended),
    }


def render_blend(blend):
    """Raport text al blend-ului sign-aware. Cu disclaimer."""
    L = [DISCLAIMER, "",
         "=== Blend sign-aware (ponderi ∝ Sharpe in-sample, conviction) ===", "",
         f"  {'factor'.ljust(10)} {'w':>7} {'Sharpe_in':>10}"]
    for name, w in blend["weights"].items():
        L.append(f"  {name.ljust(10)} {w:>7.2f} {blend['sharpe_in'][name]:>+10.2f}")
    L += ["", f"  BLEND OOS  Sharpe={blend['sharpe_oos']:+.2f}  "
              f"p={blend['p_value_oos']:.3f}  n_zile={blend['n_days_oos']}",
          "", DISCLAIMER]
    return "\n".join(L)


def render_xs(rows, n_assets=None):
    """Raport text: Sharpe full/OOS + p-value OOS per factor. Cu disclaimer."""
    L = [DISCLAIMER, "",
         "=== TIER 2b: factori cross-sectionali (long-short, net de costuri) ==="]
    if n_assets:
        L.append(f"(univers: {n_assets} active)")
    L += ["", f"  {'factor'.ljust(10)} {'Sharpe_full':>12} {'Sharpe_OOS':>12} "
              f"{'p_OOS':>8} {'n_zile':>8}"]
    for name, m in sorted(rows.items(),
                          key=lambda kv: kv[1]["sharpe_oos"], reverse=True):
        L.append(f"  {name.ljust(10)} {m['sharpe_full']:>+12.2f} "
                 f"{m['sharpe_oos']:>+12.2f} {m['p_value_oos']:>8.3f} "
                 f"{m['n_days']:>8d}")
    L += ["", DISCLAIMER]
    return "\n".join(L)
