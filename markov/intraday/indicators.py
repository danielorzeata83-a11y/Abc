"""TIER-1 quant indicators for intraday analysis.

Pure functions operating on plain numpy arrays (no Bars dependency).
No look-ahead: output[i] uses only data up to and including index i.
NaN is emitted for warmup bars where insufficient history exists.
Warmup note: price-window estimators (GK, RS, Hurst, perm. entropy, RQA,
52w-proximity, max-effect) have `window-1` leading NaNs; return-based ones
(realized_variance, bipower_variation, roll_measure) have `window` leading NaNs
because they need `window` returns = `window+1` prices. Align on a common index
before stacking features into one matrix.

Modules: volatility (Garman-Klass, Rogers-Satchell, RV, BV, jumps),
complexity (Hurst, FDI, permutation entropy, RQA determinism),
liquidity (Corwin-Schultz, Roll measure),
behavioral (52-week proximity, max effect).
"""

import math

import numpy as np

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LN2 = math.log(2.0)
_PI_OVER_2 = math.pi / 2.0


def _log_ret(close: np.ndarray) -> np.ndarray:
    """Log returns r[t] = ln(close[t] / close[t-1]), length = len(close)-1."""
    close = np.asarray(close, dtype=float)
    return np.log(close[1:] / close[:-1])


# ---------------------------------------------------------------------------
# VOLATILITY
# ---------------------------------------------------------------------------


def garman_klass(
    o: np.ndarray,
    h: np.ndarray,
    l: np.ndarray,
    c: np.ndarray,
    window: int,
) -> np.ndarray:
    """Garman-Klass volatility estimator (trailing window mean).

    Per-bar: gk = 0.5*(ln(h/l))^2 - (2*ln2 - 1)*(ln(c/o))^2
    output[i] = mean of gk over bars [i-window+1 .. i]; NaN for i < window-1.
    """
    o = np.asarray(o, dtype=float)
    h = np.asarray(h, dtype=float)
    l = np.asarray(l, dtype=float)
    c = np.asarray(c, dtype=float)
    n = len(o)
    gk = 0.5 * np.log(h / l) ** 2 - (2.0 * _LN2 - 1.0) * np.log(c / o) ** 2
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        out[i] = gk[i - window + 1 : i + 1].mean()
    return out


def rogers_satchell(
    o: np.ndarray,
    h: np.ndarray,
    l: np.ndarray,
    c: np.ndarray,
    window: int,
) -> np.ndarray:
    """Rogers-Satchell volatility estimator (trailing window mean).

    Per-bar: rs = ln(h/c)*ln(h/o) + ln(l/c)*ln(l/o)
    output[i] = mean of rs over bars [i-window+1 .. i]; NaN for i < window-1.
    """
    o = np.asarray(o, dtype=float)
    h = np.asarray(h, dtype=float)
    l = np.asarray(l, dtype=float)
    c = np.asarray(c, dtype=float)
    n = len(o)
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        out[i] = rs[i - window + 1 : i + 1].mean()
    return out


def realized_variance(close: np.ndarray, window: int) -> np.ndarray:
    """Realized variance: RV[i] = sum of r_t^2 over trailing `window` returns.

    Requires `window` returns → `window+1` prices.
    output[i] is NaN for i < window (i.e. the first `window` entries are NaN).
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    r = _log_ret(close)  # length n-1; r[j] = log return from close[j] to close[j+1]
    out = np.full(n, np.nan)
    # out[i] sums r[i-window .. i-1]   (window returns ending at close[i])
    for i in range(window, n):
        out[i] = np.sum(r[i - window : i] ** 2)
    return out


def bipower_variation(close: np.ndarray, window: int) -> np.ndarray:
    """Bipower variation: BV[i] = (pi/2) * sum_{t} |r_{t-1}|*|r_t|.

    Uses `window` consecutive log-returns (= `window+1` prices).  The sum has
    `window-1` terms: (pi/2) * sum_{k=0}^{window-2} |r[k]| * |r[k+1]|.

    NaN until `window` returns are available (first `window` entries are NaN).
    The test canonical case: window=2, 3 prices → 2 returns → 1 product.
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    r = _log_ret(close)  # length n-1; r[j] = log return ending at close[j+1]
    out = np.full(n, np.nan)
    # out[i] uses returns r[i-window .. i-1] (window returns ending at close[i])
    # First valid: i = window  (price index)
    for i in range(window, n):
        abs_r = np.abs(r[i - window : i])  # length `window`
        bv = _PI_OVER_2 * np.sum(abs_r[:-1] * abs_r[1:])
        out[i] = bv
    return out


def jump_component(
    close: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """Decompose realized variance into jump and continuous components.

    jump[i]  = max(RV[i] - BV[i], 0)
    ratio[i] = jump[i] / RV[i]  if RV[i] > 0  else 0

    Returns (jump, ratio), both of length len(close).
    NaN wherever RV or BV are NaN.
    """
    rv = realized_variance(close, window)
    bv = bipower_variation(close, window)
    n = len(close)
    jump = np.full(n, np.nan)
    ratio = np.full(n, np.nan)
    for i in range(n):
        if np.isfinite(rv[i]) and np.isfinite(bv[i]):
            j = max(rv[i] - bv[i], 0.0)
            jump[i] = j
            ratio[i] = j / rv[i] if rv[i] > 0 else 0.0
    return jump, ratio


# ---------------------------------------------------------------------------
# COMPLEXITY
# ---------------------------------------------------------------------------


def _rs_hurst(prices: np.ndarray) -> float:
    """Estimate Hurst exponent via R/S analysis.

    R/S analysis is applied to log-returns (first differences of log prices).
    Sub-lengths span roughly 4 octaves: n//8, n//4, n//2, n of the return
    series.  Hurst = OLS slope of log(mean R/S) vs log(sub-length).

    Returns 0.5 if estimation fails (too few points / zero variance).
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 9:
        return 0.5
    # Work on log-returns so that R/S analysis is on stationary increments
    log_r = np.diff(np.log(np.where(prices > 0, prices, np.abs(prices) + 1e-12)))
    n = len(log_r)
    if n < 4:
        return 0.5

    # Build sub-lengths: start at max(4, n//8) doubling up to n
    min_len = max(4, n // 8)
    sub_lens = []
    s = min_len
    while s <= n:
        sub_lens.append(s)
        s = s * 2
    if len(sub_lens) < 2:
        # Ensure at least 2 distinct scales
        sub_lens = sorted({max(4, n // 4), n})

    log_n_list = []
    log_rs_list = []
    for sub in sub_lens:
        num_chunks = n // sub
        if num_chunks == 0:
            continue
        rs_vals = []
        for k in range(num_chunks):
            chunk = log_r[k * sub : (k + 1) * sub]
            mean_c = chunk.mean()
            dev = np.cumsum(chunk - mean_c)
            r = dev.max() - dev.min()
            s_std = chunk.std(ddof=1)
            if s_std > 0:
                rs_vals.append(r / s_std)
        if rs_vals:
            log_n_list.append(math.log(sub))
            log_rs_list.append(math.log(np.mean(rs_vals)))

    if len(log_n_list) < 2:
        return 0.5
    # OLS slope
    log_n = np.array(log_n_list)
    log_rs = np.array(log_rs_list)
    x_bar = log_n.mean()
    y_bar = log_rs.mean()
    den = np.sum((log_n - x_bar) ** 2)
    if den == 0:
        return 0.5
    num = np.sum((log_n - x_bar) * (log_rs - y_bar))
    return float(num / den)


def hurst(close: np.ndarray, window: int) -> np.ndarray:
    """Rolling Hurst exponent via Rescaled-Range (R/S) analysis.

    H ≈ 0.5  → random walk
    H > 0.5  → trending / persistent
    H < 0.5  → mean-reverting / anti-persistent

    NaN for the first `window-1` entries.
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        window_slice = close[i - window + 1 : i + 1]
        out[i] = _rs_hurst(window_slice)
    return out


def fdi(close: np.ndarray, window: int) -> np.ndarray:
    """Fractal Dimension Index: FDI = 2 - H (derived from Hurst exponent).

    FDI > 1.5 → mean-reverting; FDI < 1.5 → trending.
    """
    return 2.0 - hurst(close, window)


def permutation_entropy(
    close: np.ndarray, m: int, window: int
) -> np.ndarray:
    """Rolling permutation entropy, normalized to [0, 1].

    For each trailing `window` of prices, count the frequencies of all ordinal
    patterns of length `m`. Entropy = -sum(p * log(p)) / log(m!).

    NaN for first `window-1` entries.
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = np.full(n, np.nan)
    max_entropy = math.log(math.factorial(m))
    if max_entropy == 0:
        return out
    for i in range(window - 1, n):
        segment = close[i - window + 1 : i + 1]
        # Extract all m-grams and compute their ordinal patterns
        patterns: dict = {}
        total = 0
        for j in range(len(segment) - m + 1):
            gram = segment[j : j + m]
            pat = tuple(np.argsort(gram))
            patterns[pat] = patterns.get(pat, 0) + 1
            total += 1
        if total == 0:
            continue
        entropy = 0.0
        for count in patterns.values():
            p = count / total
            entropy -= p * math.log(p)
        out[i] = entropy / max_entropy
    return out


def rqa_determinism(
    close: np.ndarray, window: int, eps: float
) -> np.ndarray:
    """Rolling Recurrence Quantification Analysis — Determinism (DET).

    DET = (recurrence points on diagonal lines of length >= 2, excl. main
           diagonal) / (total recurrence points excl. main diagonal).

    Parameters
    ----------
    window : int
        Must be <= 200 (raises ValueError otherwise) to bound O(window^2) cost.
    eps : float
        Threshold for recurrence: |x_i - x_j| <= eps.

    Returns values in [0, 1]; NaN for warmup and when no off-diagonal
    recurrences exist.
    """
    if window > 200:
        raise ValueError(
            f"rqa_determinism: window={window} exceeds the maximum of 200 "
            "(computational guard against O(window^2) memory)."
        )
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        x = close[i - window + 1 : i + 1]
        w = len(x)
        # Build recurrence matrix (exclude main diagonal automatically)
        diff = np.abs(x[:, None] - x[None, :])
        rec = diff <= eps
        # Zero out main diagonal
        np.fill_diagonal(rec, False)
        total_rec = int(rec.sum())
        if total_rec == 0:
            out[i] = 0.0
            continue
        # Count recurrence points that lie on diagonal lines of length >= 2.
        # Iterate over every diagonal (excluding main), find runs of True, and
        # accumulate points belonging to runs of length >= 2.
        diag_points = 0
        for d in range(-(w - 1), w):
            if d == 0:
                continue
            diag = np.diag(rec, d)
            # find runs of True and accumulate points in runs >=2
            run_len = 0
            for val in diag:
                if val:
                    run_len += 1
                else:
                    if run_len >= 2:
                        diag_points += run_len
                    run_len = 0
            if run_len >= 2:
                diag_points += run_len
        out[i] = diag_points / total_rec
    return out


# ---------------------------------------------------------------------------
# LIQUIDITY
# ---------------------------------------------------------------------------


def corwin_schultz(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """Corwin-Schultz two-bar bid-ask spread estimator.

    For each i >= 1:
        beta  = (ln(h_i/l_i))^2 + (ln(h_{i-1}/l_{i-1}))^2
        gamma = (ln(max(h_i, h_{i-1}) / min(l_i, l_{i-1})))^2
        k     = 3 - 2*sqrt(2)
        alpha = (sqrt(2*beta) - sqrt(beta)) / k - sqrt(gamma / k)
        spread = 2*(exp(alpha)-1)/(1+exp(alpha)), clipped to >= 0.

    output[0] = NaN.
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    n = len(high)
    out = np.full(n, np.nan)
    k = 3.0 - 2.0 * math.sqrt(2.0)
    for i in range(1, n):
        hl_i = math.log(high[i] / low[i])
        hl_i1 = math.log(high[i - 1] / low[i - 1])
        beta = hl_i ** 2 + hl_i1 ** 2
        gamma = (math.log(max(high[i], high[i - 1]) / min(low[i], low[i - 1]))) ** 2
        alpha = (math.sqrt(2.0 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
        spread = 2.0 * (math.exp(alpha) - 1.0) / (1.0 + math.exp(alpha))
        out[i] = max(spread, 0.0)
    return out


def roll_measure(close: np.ndarray, window: int) -> np.ndarray:
    """Roll (1984) effective bid-ask spread estimator.

    For each trailing `window` of price changes dP:
        cov = Cov(dP_t, dP_{t-1})
        Roll = 2 * sqrt(-cov)  if cov < 0  else 0.

    NaN until enough data (first `window+1` entries NaN).
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    dp = np.diff(close)  # length n-1
    out = np.full(n, np.nan)
    # We need `window` dP values plus their lag-1 pair, so `window` products
    # dp[t]*dp[t-1] — these are available from dp index 1 onwards.
    # For price index i, use dp[i-window .. i-1] (window consecutive changes
    # ending at close[i]).  Cov needs at least 2 values (window >= 2).
    for i in range(window, n):
        chunk = dp[i - window : i]  # `window` values
        if len(chunk) < 2:
            continue
        cov = np.cov(chunk[:-1], chunk[1:])[0, 1]
        out[i] = 2.0 * math.sqrt(-cov) if cov < 0.0 else 0.0
    return out


# ---------------------------------------------------------------------------
# BEHAVIORAL
# ---------------------------------------------------------------------------


def high_52w_proximity(close: np.ndarray, lookback: int) -> np.ndarray:
    """Proximity to 52-week (or `lookback`-bar) high.

    output[i] = close[i] / max(close[i-lookback+1 .. i])
    NaN for i < lookback - 1.
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = np.full(n, np.nan)
    for i in range(lookback - 1, n):
        rolling_max = close[i - lookback + 1 : i + 1].max()
        out[i] = close[i] / rolling_max
    return out


def max_effect(daily_returns: np.ndarray, window: int) -> np.ndarray:
    """Trailing rolling maximum of `daily_returns` over `window` bars.

    output[i] = max(daily_returns[i-window+1 .. i])
    NaN for i < window - 1.
    """
    daily_returns = np.asarray(daily_returns, dtype=float)
    n = len(daily_returns)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        out[i] = daily_returns[i - window + 1 : i + 1].max()
    return out
