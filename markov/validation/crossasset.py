"""TIER 2: retea lead-lag cross-asset din transfer entropy.

Aliniaza randamentele zilnice pe date comune, apoi calculeaza matricea TE(i->j)
intre toate perechile. Scorul NET (flux iesit - flux intrat) clasifica activele in
"lideri" (informeaza pe altii) vs "urmaritori". Functii pure peste cache.

NU este consiliere de investitii.
"""

import numpy as np
import pandas as pd

from markov.data_providers import DataUnavailable
from markov.intraday.bars import resample
from markov.intraday.cache import read_bars
from markov.validation.transfer_entropy import transfer_entropy


def aligned_returns(symbols, data_dir, horizon_tf="1day"):
    """DataFrame de randamente zilnice aliniate pe datele comune tuturor simbolurilor."""
    closes = {}
    for s in symbols:
        b = read_bars(data_dir, s)
        if b is None:
            raise DataUnavailable(f"fara cache pentru {s}")
        b = resample(b, horizon_tf) if horizon_tf != "15m" else b
        df = b.to_frame()
        closes[s] = pd.Series(np.asarray(df["close"], dtype=float),
                              index=pd.DatetimeIndex(df.index))
    panel = pd.DataFrame(closes).sort_index()
    return panel.pct_change().dropna(how="any")


def lead_lag_matrix(rets, bins=4, lag=1):
    """(simboluri, matrice TE[i->j], scor_net). net[i] = iesit(i) - intrat(i)."""
    syms = list(rets.columns)
    k = len(syms)
    M = np.full((k, k), np.nan)
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            M[i, j] = transfer_entropy(rets[syms[i]].to_numpy(),
                                       rets[syms[j]].to_numpy(), bins, lag)
    net = np.nansum(M, axis=1) - np.nansum(M, axis=0)   # iesit - intrat
    return syms, M, net


def render_lead_lag(syms, M, net):
    """Text: matricea TE + clasamentul lider->urmaritor dupa scorul net."""
    DISC = "NU este consiliere de investitii. Artefact de cercetare."
    L = [DISC, "", "=== Retea lead-lag (transfer entropy, nats) ===", "",
         "TE(rand->col):"]
    L.append("        " + "".join(s.rjust(9) for s in syms))
    for i, s in enumerate(syms):
        row = s.ljust(8)
        for j in range(len(syms)):
            row += ("    -    " if i == j else f"{M[i, j]:.4f}".rjust(9))
        L.append(row)
    L.append("")
    L.append("Scor net (iesit-intrat) -- pozitiv = lider:")
    for i in np.argsort(net)[::-1]:
        rol = "lider" if net[i] > 0 else "urmaritor"
        L.append(f"  {syms[i].ljust(8)}{net[i]:+.4f}  ({rol})")
    L.append("")
    L.append(DISC)
    return "\n".join(L)
