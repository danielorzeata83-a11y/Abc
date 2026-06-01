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
