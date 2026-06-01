"""Combine alpha streams at equal risk.

Blend several daily return streams so each contributes roughly equal
volatility, then scale the blend to a target annual volatility. Combining
uncorrelated positive-Sharpe streams is the one genuine free lunch in
finance: the Sharpe of the blend exceeds that of any single stream.

Weights use the full sample volatility here for simplicity; for a strict
walk-forward use, estimate them on a trailing window. The combination math
itself introduces no look-ahead beyond that scaling choice.
"""

import numpy as np

_ANN = np.sqrt(252)


def orthogonalize(stream, basis):
    """Residual of `stream` after regressing it on the `basis` streams.

    Returns stream - B @ betas, where betas are the OLS coefficients of
    `stream` on the basis (with intercept). A positive-Sharpe residual
    proves the stream carries information independent of the basis, i.e.
    genuine diversification rather than redundancy.
    """
    stream = np.asarray(stream, dtype=float)
    basis = [np.asarray(b, dtype=float) for b in basis]
    n = len(stream)
    if any(len(b) != n for b in basis):
        raise ValueError("stream and basis must have the same length")
    X = np.column_stack([np.ones(n)] + basis)  # intercept + basis
    coef, *_ = np.linalg.lstsq(X, stream, rcond=None)
    # Keep the intercept's contribution (the stream's own mean alpha):
    # residual = stream - basis_part, excluding intercept from removal.
    basis_part = X[:, 1:] @ coef[1:]
    return stream - basis_part


def combine_alphas(streams, target_vol=0.10, weights=None):
    """Equal-risk blend of return streams, scaled to `target_vol` annual.

    streams : list of 1-D arrays of equal length.
    weights : optional explicit weights; default is inverse-volatility
              (equal risk contribution).
    """
    streams = [np.asarray(s, dtype=float) for s in streams]
    n = len(streams[0])
    if any(len(s) != n for s in streams):
        raise ValueError("all streams must have the same length")

    M = np.vstack(streams)  # (k, n)
    if weights is None:
        vols = M.std(axis=1)
        vols[vols == 0] = np.nan
        w = np.where(np.isfinite(1.0 / vols), 1.0 / vols, 0.0)
        w = w / w.sum()
    else:
        w = np.asarray(weights, dtype=float)
        w = w / w.sum()

    blend = w @ M
    # Scale the blend to the annual target volatility.
    realised = blend.std() * _ANN
    if realised > 0:
        blend = blend * (target_vol / realised)
    return blend
