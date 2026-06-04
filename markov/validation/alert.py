"""Raport zilnic al motorului -> Telegram: prognoza de volatilitate per simbol
(semnalul realized_var, validat OOS, IC~0.41) + reteaua lead-lag (cine conduce).

Functii pure pentru continut; trimiterea se face cu markov.telegram.send_message.
NU este consiliere de investitii.
"""

import numpy as np

from markov.intraday.bars import resample
from markov.intraday.cache import read_bars
from markov.validation import tier1
from markov.validation.crossasset import aligned_returns, lead_lag_matrix
from markov.validation.ensemble import zscore_causal

DISCLAIMER = "NU este consiliere de investitii."


def current_vol_signal(bars):
    """z-score cauzal al realized_var la ultima bara: >0 = vol peste media istorica.

    realized_var de azi prezice vol-ul forward (IC~0.41 OOS), deci z-ul curent E
    prognoza de risc. Intoarce nan daca nu exista valoare finita."""
    rv = tier1.INDICATORS["realized_var"](bars)
    z = zscore_causal(np.asarray(rv, dtype=float))
    fin = z[np.isfinite(z)]
    return float(fin[-1]) if len(fin) else float("nan")


def _vol_label(z):
    if not np.isfinite(z):
        return "fara date"
    if z >= 1.0:
        return "RIDICATA -> redu expunerea"
    if z <= -1.0:
        return "SCAZUTA"
    return "normala"


def collect_vol(symbols, data_dir, horizon_tf="1day"):
    """[(simbol, z, eticheta)] sortat descrescator dupa z (cele mai fierbinti sus)."""
    rows = []
    for s in symbols:
        b = read_bars(data_dir, s)
        if b is None:
            rows.append((s, float("nan"), "fara cache"))
            continue
        b = resample(b, horizon_tf) if horizon_tf != "15m" else b
        z = current_vol_signal(b)
        rows.append((s, z, _vol_label(z)))
    rows.sort(key=lambda r: (np.isfinite(r[1]), r[1]), reverse=True)
    return rows


def build_engine_alert(asof, vol_rows, leaders):
    """Mesaj text: volatilitate per simbol + clasament lead-lag. Cu disclaimer.

    vol_rows: [(simbol, z, eticheta)]; leaders: [(simbol, net_score)] sortat desc."""
    L = [f"Abc -- motor ({asof})", "",
         "VOLATILITATE (z realized_var, ridicat = risc forward mai mare):"]
    for sym, z, label in vol_rows:
        zt = f"{z:+.2f}" if np.isfinite(z) else "  n/a"
        L.append(f"- {sym.ljust(6)} z={zt}  {label}")
    L += ["", "LEAD-LAG (cine conduce, transfer entropy net):"]
    for sym, net in leaders:
        rol = "lider" if net > 0 else "urmaritor"
        L.append(f"- {sym.ljust(6)} {net:+.4f}  ({rol})")
    L += ["", DISCLAIMER]
    return "\n".join(L)


def build_from_cache(symbols, data_dir, asof, bins=4, lag=1):
    """Orchestreaza: vol per simbol + lead-lag din cache -> mesajul gata de trimis."""
    vol_rows = collect_vol(symbols, data_dir)
    rets = aligned_returns(symbols, data_dir)
    syms, _M, net = lead_lag_matrix(rets, bins=bins, lag=lag)
    order = np.argsort(net)[::-1]
    leaders = [(syms[i], float(net[i])) for i in order]
    return build_engine_alert(asof, vol_rows, leaders)
