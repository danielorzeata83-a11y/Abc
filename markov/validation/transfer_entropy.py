"""TIER 2 (cross-asset): Transfer Entropy TE(X->Y) -- flux de informatie directionala.

TE(X->Y) = cat reduce trecutul lui X incertitudinea asupra viitorului lui Y, PESTE
ce stie deja trecutul lui Y. Asimetric (TE(X->Y) != TE(Y->X)) -> detecteaza "cine
conduce pe cine", non-liniar, spre deosebire de corelatie. Estimator pe histograme
(binare pe cuantile), functii pure numpy.

  TE(X->Y) = H(Y_t+ | Y_t) - H(Y_t+ | Y_t, X_t)
           = [H(Y+,Y) - H(Y)] - [H(Y+,Y,X) - H(Y,X)]

NU este consiliere de investitii.
"""

import numpy as np


def _digitize(a, bins):
    """Discretizeaza in `bins` cosuri egale ca probabilitate (cuantile). 0..bins-1."""
    edges = np.quantile(a, np.linspace(0.0, 1.0, bins + 1)[1:-1])
    return np.digitize(a, edges)


def _entropy(*cols, bins):
    """Entropie Shannon (nats) a distributiei comune a coloanelor int-codate."""
    codes = np.zeros(len(cols[0]), dtype=np.int64)
    for i, c in enumerate(cols):
        codes += c.astype(np.int64) * (bins ** i)
    _, counts = np.unique(codes, return_counts=True)
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p)))


def transfer_entropy(x, y, bins=4, lag=1):
    """TE(x->y): fluxul de informatie de la x catre y la `lag` pasi. >= 0 (nats).

    Aliniaza pe pozitiile finite comune, discretizeaza pe cuantile, estimeaza pe
    histograme. Intoarce nan daca prea putine date pentru `bins` cosuri."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < max(20, bins ** 3) + lag:
        return float("nan")
    xb, yb = _digitize(x, bins), _digitize(y, bins)
    yf = yb[lag:]          # viitorul lui Y
    yp = yb[:-lag]         # trecutul lui Y
    xp = xb[:-lag]         # trecutul lui X
    te = ((_entropy(yf, yp, bins=bins) - _entropy(yp, bins=bins))
          - (_entropy(yf, yp, xp, bins=bins) - _entropy(yp, xp, bins=bins)))
    return max(te, 0.0)    # TE teoretic >= 0; taiem zgomotul de estimare


def net_transfer_entropy(x, y, bins=4, lag=1):
    """TE(x->y) - TE(y->x): dominanta directionala neta (>0 daca x conduce y)."""
    fwd = transfer_entropy(x, y, bins, lag)
    bwd = transfer_entropy(y, x, bins, lag)
    if not (np.isfinite(fwd) and np.isfinite(bwd)):
        return float("nan")
    return fwd - bwd
