"""Cross-sectional latest-position signals for a target asset.

Given a panel (T, N) and a target column, each signal ranks the universe
on the latest bar and maps the target's rank to a position in [-1, 1].
This is where the project's validated alpha lives (reversal, illiquidity,
residual momentum) -- a single asset is signalled by its standing within
the universe. Reuses the tested score functions; no look-ahead.
"""

import numpy as np

from markov.amihud import illiquidity_scores
from markov.resmom import residual_momentum_scores


def rank_position(scores, target_idx, direction=1):
    """Map the target's cross-sectional rank to a position in [-1, 1].

    direction=+1 -> long high score; -1 -> long low score. The top-ranked
    asset gets +/-1, the bottom -/+1, the median ~0.
    """
    scores = np.asarray(scores, dtype=float)
    n = len(scores)
    order = scores.argsort()
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(n)
    centered = ranks[target_idx] / (n - 1) - 0.5  # [-0.5, 0.5]
    return float(direction * 2.0 * centered)


def reversal_position(prices, target_idx, lookback=10):
    """Reversal: long recent losers (direction=-1 on trailing return)."""
    prices = np.asarray(prices, dtype=float)
    if not 0 <= target_idx < prices.shape[1]:
        raise IndexError(f"target_idx {target_idx} out of range")
    scores = prices[-1] / prices[-1 - lookback] - 1.0
    return rank_position(scores, target_idx, direction=-1)


def amihud_position(prices, volume, target_idx, window=20):
    """Illiquidity: long the illiquid (direction=+1 on Amihud score)."""
    prices = np.asarray(prices, dtype=float)
    if not 0 <= target_idx < prices.shape[1]:
        raise IndexError(f"target_idx {target_idx} out of range")
    scores = illiquidity_scores(prices, np.asarray(volume, dtype=float),
                                t=prices.shape[0] - 1, window=window)
    fin = np.isfinite(scores)
    scores = np.where(fin, scores, np.nanmedian(scores[fin]) if fin.any() else 0.0)
    return rank_position(scores, target_idx, direction=+1)


def resmom_position(prices, target_idx, lookback=126, skip=21):
    """Residual momentum: long idiosyncratic winners (direction=+1)."""
    prices = np.asarray(prices, dtype=float)
    if not 0 <= target_idx < prices.shape[1]:
        raise IndexError(f"target_idx {target_idx} out of range")
    scores = residual_momentum_scores(prices, t=prices.shape[0] - 1,
                                      lookback=lookback, skip=skip)
    return rank_position(scores, target_idx, direction=+1)
