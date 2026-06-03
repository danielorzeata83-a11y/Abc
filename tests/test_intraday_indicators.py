"""Tests for TIER-1 intraday quantitative indicators.

Pure-numpy functions operating on plain numpy arrays (no Bars dependency).
Tests cover exact hand-computed values where formulas allow, and ordinal/range
assertions for estimators whose ground truth is stochastic.
"""

import math

import numpy as np
import pytest

from markov.intraday.indicators import (
    garman_klass,
    rogers_satchell,
    realized_variance,
    bipower_variation,
    jump_component,
    hurst,
    fdi,
    permutation_entropy,
    rqa_determinism,
    corwin_schultz,
    roll_measure,
    high_52w_proximity,
    max_effect,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
LN2 = math.log(2)


# ===========================================================================
# VOLATILITY
# ===========================================================================


class TestGarmanKlass:
    def test_nan_before_window(self):
        o = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        h = np.array([2.0, 2.0, 2.0, 2.0, 2.0])
        l = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        c = np.array([1.5, 1.5, 1.5, 1.5, 1.5])
        result = garman_klass(o, h, l, c, window=4)
        assert np.all(np.isnan(result[:3]))
        assert np.isfinite(result[3])

    def test_exact_last_value(self):
        # Single bar, window=1 → output[0] = per-bar GK value
        o = np.array([10.0])
        h = np.array([12.0])
        l = np.array([9.0])
        c = np.array([11.0])
        expected_gk = 0.5 * (math.log(12 / 9)) ** 2 - (2 * LN2 - 1) * (
            math.log(11 / 10)
        ) ** 2
        result = garman_klass(o, h, l, c, window=1)
        assert result[0] == pytest.approx(expected_gk, rel=1e-9)

    def test_window_of_two_exact(self):
        # window=2, last value = mean of bar[0] and bar[1] GK values
        o = np.array([10.0, 20.0])
        h = np.array([12.0, 22.0])
        l = np.array([9.0, 18.0])
        c = np.array([11.0, 21.0])
        gk0 = 0.5 * (math.log(12 / 9)) ** 2 - (2 * LN2 - 1) * (math.log(11 / 10)) ** 2
        gk1 = 0.5 * (math.log(22 / 18)) ** 2 - (2 * LN2 - 1) * (math.log(21 / 20)) ** 2
        result = garman_klass(o, h, l, c, window=2)
        assert np.isnan(result[0])
        assert result[1] == pytest.approx((gk0 + gk1) / 2, rel=1e-9)

    def test_output_length(self):
        n = 20
        o = h = l = c = np.ones(n)
        assert len(garman_klass(o, h, l, c, window=5)) == n


class TestRogersSatchell:
    def test_nan_before_window(self):
        o = np.ones(5)
        h = np.ones(5) * 2
        l = np.ones(5) * 0.5
        c = np.ones(5)
        result = rogers_satchell(o, h, l, c, window=3)
        assert np.all(np.isnan(result[:2]))
        assert np.isfinite(result[2])

    def test_exact_single_bar(self):
        # rs = ln(h/c)*ln(h/o) + ln(l/c)*ln(l/o)
        o = np.array([10.0])
        h = np.array([12.0])
        l = np.array([9.0])
        c = np.array([11.0])
        expected = math.log(12 / 11) * math.log(12 / 10) + math.log(9 / 11) * math.log(
            9 / 10
        )
        result = rogers_satchell(o, h, l, c, window=1)
        assert result[0] == pytest.approx(expected, rel=1e-9)

    def test_output_length(self):
        n = 10
        assert len(rogers_satchell(np.ones(n), np.ones(n), np.ones(n), np.ones(n), 3)) == n


class TestRealizedVariance:
    def test_nan_before_window(self):
        # window=3 needs 3 returns (4 prices); first 3 outputs = NaN
        c = np.array([1.0, 2.0, 4.0, 8.0, 16.0])
        result = realized_variance(c, window=3)
        # indices 0,1,2 are NaN (not enough returns yet)
        assert np.all(np.isnan(result[:3]))
        assert np.isfinite(result[3])

    def test_exact_value(self):
        # closes: 1,2,4 → log returns: ln2, ln2; RV = ln2^2 + ln2^2
        c = np.array([1.0, 2.0, 4.0])
        result = realized_variance(c, window=2)
        expected = 2 * (math.log(2)) ** 2
        assert result[-1] == pytest.approx(expected, rel=1e-9)

    def test_nonnegative(self):
        rng = np.random.default_rng(42)
        c = 100 + np.cumsum(rng.normal(0, 1, 100))
        rv = realized_variance(c, window=20)
        assert np.all(rv[~np.isnan(rv)] >= 0)


class TestBipowerVariation:
    def test_finite_nonnegative(self):
        rng = np.random.default_rng(7)
        c = 100 + np.cumsum(rng.normal(0, 1, 60))
        bv = bipower_variation(c, window=20)
        valid = bv[~np.isnan(bv)]
        assert len(valid) > 0
        assert np.all(valid >= 0)
        assert np.all(np.isfinite(valid))

    def test_nan_warmup(self):
        c = np.arange(1.0, 11.0)
        bv = bipower_variation(c, window=5)
        assert np.all(np.isnan(bv[:5]))

    def test_exact_two_returns(self):
        # 3 prices → 2 returns r0, r1; BV with window=2
        # BV = (pi/2) * |r0|*|r1|
        c = np.array([1.0, math.e, math.e ** 2])
        # returns: 1.0, 1.0 (both = ln(e))
        result = bipower_variation(c, window=2)
        expected = (math.pi / 2) * 1.0 * 1.0
        assert result[-1] == pytest.approx(expected, rel=1e-9)


class TestJumpComponent:
    def test_jump_with_large_outlier(self):
        rng = np.random.default_rng(99)
        # 50 bars of smooth, then one large jump
        c = np.concatenate(
            [100 + np.arange(50, dtype=float), np.array([200.0, 201.0, 202.0])]
        )
        jump, ratio = jump_component(c, window=10)
        # At the position containing the large jump, jump > 0 and ratio > 0
        valid_j = jump[~np.isnan(jump)]
        valid_r = ratio[~np.isnan(ratio)]
        assert np.any(valid_j > 0)
        assert np.any(valid_r > 0)

    def test_smooth_ramp_no_jump(self):
        # Perfectly linear price series: returns are constant, no jumps
        c = np.arange(1.0, 50.0)
        jump, ratio = jump_component(c, window=10)
        valid_j = jump[~np.isnan(jump)]
        # All jumps should be ~0 for constant returns
        assert np.all(valid_j < 1e-10)

    def test_jump_nonnegative(self):
        rng = np.random.default_rng(5)
        c = 100 + np.cumsum(rng.normal(0, 1, 80))
        jump, ratio = jump_component(c, window=15)
        valid = jump[~np.isnan(jump)]
        assert np.all(valid >= 0)

    def test_ratio_in_unit_interval(self):
        rng = np.random.default_rng(6)
        c = 100 + np.cumsum(rng.normal(0, 1, 80))
        jump, ratio = jump_component(c, window=15)
        valid = ratio[~np.isnan(ratio)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 1.0 + 1e-12)

    def test_shapes_match(self):
        c = np.arange(1.0, 30.0)
        j, r = jump_component(c, window=5)
        assert j.shape == r.shape == c.shape


# ===========================================================================
# COMPLEXITY
# ===========================================================================


class TestHurst:
    def test_random_walk_near_half(self):
        rng = np.random.default_rng(0)
        c = np.cumsum(rng.normal(0, 1, 500))
        h = hurst(c, window=400)
        last = h[~np.isnan(h)][-1]
        assert 0.35 <= last <= 0.65

    def test_strong_trend_above_half(self):
        c = np.arange(1.0, 400.0)  # perfect linear trend
        h = hurst(c, window=200)
        last = h[~np.isnan(h)][-1]
        assert last > 0.55

    def test_alternating_mean_revert_below_half(self):
        # Alternating: +1, -1, +1, -1, ... → anti-persistent
        vals = np.empty(400)
        vals[0] = 100.0
        for i in range(1, 400):
            vals[i] = vals[i - 1] + (1 if i % 2 == 0 else -1)
        h = hurst(vals, window=200)
        last = h[~np.isnan(h)][-1]
        assert last < 0.5

    def test_nan_warmup(self):
        c = np.arange(1.0, 100.0)
        h = hurst(c, window=50)
        assert np.all(np.isnan(h[:49]))

    def test_output_length(self):
        c = np.arange(1.0, 200.0)
        assert len(hurst(c, window=100)) == len(c)


class TestFdi:
    def test_fdi_equals_2_minus_hurst(self):
        rng = np.random.default_rng(42)
        c = 100 + np.cumsum(rng.normal(0, 1, 300))
        h = hurst(c, window=100)
        f = fdi(c, window=100)
        mask = np.isfinite(h) & np.isfinite(f)
        assert np.allclose(f[mask], 2.0 - h[mask], atol=1e-12)

    def test_output_length(self):
        c = np.arange(1.0, 150.0)
        assert len(fdi(c, window=50)) == len(c)


class TestPermutationEntropy:
    def test_iid_noise_high_entropy(self):
        rng = np.random.default_rng(11)
        c = rng.normal(0, 1, 500)
        pe = permutation_entropy(c, m=3, window=200)
        last = pe[~np.isnan(pe)][-1]
        assert last > 0.8

    def test_monotonic_low_entropy(self):
        c = np.arange(1.0, 300.0)  # strictly increasing
        pe = permutation_entropy(c, m=3, window=100)
        last = pe[~np.isnan(pe)][-1]
        assert last < 0.2

    def test_output_in_unit_interval(self):
        rng = np.random.default_rng(3)
        c = rng.normal(0, 1, 200)
        pe = permutation_entropy(c, m=3, window=50)
        valid = pe[~np.isnan(pe)]
        assert np.all(valid >= 0) and np.all(valid <= 1.0 + 1e-12)

    def test_nan_warmup(self):
        c = np.arange(1.0, 60.0)
        pe = permutation_entropy(c, m=3, window=30)
        assert np.all(np.isnan(pe[:29]))

    def test_output_length(self):
        c = np.arange(1.0, 100.0)
        assert len(permutation_entropy(c, m=3, window=20)) == len(c)


class TestRqaDeterminism:
    def test_sine_wave_high_det(self):
        t = np.linspace(0, 4 * math.pi, 200)
        c = np.sin(t)
        det = rqa_determinism(c, window=100, eps=0.2)
        last = det[~np.isnan(det)][-1]
        assert last > 0.7

    def test_noise_lower_det(self):
        rng = np.random.default_rng(77)
        c = rng.normal(0, 1, 200)
        det_sine = rqa_determinism(np.sin(np.linspace(0, 4 * math.pi, 200)), window=100, eps=0.2)
        det_noise = rqa_determinism(c, window=100, eps=0.2)
        # Sine DET > noise DET (use last valid values)
        sine_last = det_sine[~np.isnan(det_sine)][-1]
        noise_last = det_noise[~np.isnan(det_noise)][-1]
        assert sine_last > noise_last

    def test_window_too_large_raises(self):
        c = np.arange(1.0, 300.0)
        with pytest.raises(ValueError):
            rqa_determinism(c, window=201, eps=0.1)

    def test_output_in_unit_interval(self):
        t = np.linspace(0, 2 * math.pi, 150)
        c = np.sin(t)
        det = rqa_determinism(c, window=50, eps=0.2)
        valid = det[~np.isnan(det)]
        assert np.all(valid >= 0) and np.all(valid <= 1.0 + 1e-12)

    def test_output_length(self):
        c = np.sin(np.linspace(0, 2 * math.pi, 100))
        assert len(rqa_determinism(c, window=50, eps=0.2)) == len(c)


# ===========================================================================
# LIQUIDITY
# ===========================================================================


class TestCorwinSchultz:
    def test_first_output_nan(self):
        h = np.array([2.0, 3.0, 4.0])
        l = np.array([1.0, 2.0, 3.0])
        cs = corwin_schultz(h, l)
        assert np.isnan(cs[0])

    def test_exact_last_value(self):
        # 3 bars: use bars 1 and 2 (i=2 in 0-indexed)
        h = np.array([12.0, 14.0, 13.0])
        l = np.array([9.0, 10.0, 11.0])
        # beta for i=2: (ln(13/11))^2 + (ln(14/10))^2
        beta = (math.log(13 / 11)) ** 2 + (math.log(14 / 10)) ** 2
        # gamma: (ln(max(14,13)/min(10,11)))^2
        gamma = (math.log(max(14, 13) / min(10, 11))) ** 2
        k = 3 - 2 * math.sqrt(2)
        alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
        spread = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
        spread = max(spread, 0.0)
        cs = corwin_schultz(h, l)
        assert cs[2] == pytest.approx(spread, rel=1e-9)

    def test_nonnegative(self):
        rng = np.random.default_rng(55)
        prices = 100 + np.cumsum(rng.normal(0, 0.5, 50))
        h = prices + rng.uniform(0, 1, 50)
        l = prices - rng.uniform(0, 1, 50)
        cs = corwin_schultz(h, l)
        valid = cs[~np.isnan(cs)]
        assert np.all(valid >= 0)

    def test_output_length(self):
        n = 20
        h = np.ones(n) * 2
        l = np.ones(n)
        assert len(corwin_schultz(h, l)) == n


class TestRollMeasure:
    def test_bid_ask_bounce_positive_roll(self):
        # Alternating +/- price changes → strong negative serial correlation
        # prices: 100, 101, 100, 101, 100, ...
        c = np.array([100.0 + (i % 2) for i in range(50)])
        roll = roll_measure(c, window=20)
        valid = roll[~np.isnan(roll)]
        assert np.any(valid > 0)

    def test_trending_series_zero_roll(self):
        c = np.arange(1.0, 60.0)  # perfectly linear up-trend
        roll = roll_measure(c, window=20)
        valid = roll[~np.isnan(roll)]
        # Trending → cov >= 0 → Roll = 0
        assert np.all(valid == 0)

    def test_nonnegative(self):
        rng = np.random.default_rng(12)
        c = 100 + np.cumsum(rng.normal(0, 1, 80))
        roll = roll_measure(c, window=20)
        valid = roll[~np.isnan(roll)]
        assert np.all(valid >= 0)

    def test_output_length(self):
        c = np.arange(1.0, 50.0)
        assert len(roll_measure(c, window=10)) == len(c)


# ===========================================================================
# BEHAVIORAL
# ===========================================================================


class TestHigh52wProximity:
    def test_new_high_equals_one(self):
        # Monotonically increasing → always at new highs
        c = np.arange(1.0, 20.0)
        prox = high_52w_proximity(c, lookback=10)
        valid = prox[~np.isnan(prox)]
        assert np.all(valid == pytest.approx(1.0))

    def test_below_max_less_than_one(self):
        # 20 rising then 5 dropping
        c = np.concatenate([np.arange(1.0, 21.0), np.array([15.0, 14.0, 13.0, 12.0, 11.0])])
        prox = high_52w_proximity(c, lookback=10)
        # Last few values should be < 1 since close < rolling max
        assert prox[-1] < 1.0

    def test_nan_warmup(self):
        c = np.arange(1.0, 30.0)
        prox = high_52w_proximity(c, lookback=10)
        assert np.all(np.isnan(prox[:9]))

    def test_exact_value(self):
        # close=8, max(last 5) = 10 → proximity = 8/10 = 0.8
        c = np.array([5.0, 10.0, 8.0, 7.0, 6.0, 8.0])
        prox = high_52w_proximity(c, lookback=5)
        # At index 5: window=[10,8,7,6,8], max=10, close=8, ratio=0.8
        assert prox[5] == pytest.approx(0.8, rel=1e-9)

    def test_output_length(self):
        c = np.arange(1.0, 50.0)
        assert len(high_52w_proximity(c, lookback=10)) == len(c)


class TestMaxEffect:
    def test_exact_value(self):
        # daily returns = [0.1, 0.2, 0.05, 0.3, 0.15], window=3
        # last window: [0.05, 0.3, 0.15] → max = 0.3
        dr = np.array([0.1, 0.2, 0.05, 0.3, 0.15])
        me = max_effect(dr, window=3)
        assert me[-1] == pytest.approx(0.3, rel=1e-9)

    def test_nan_warmup(self):
        dr = np.arange(0.0, 20.0)
        me = max_effect(dr, window=5)
        assert np.all(np.isnan(me[:4]))

    def test_equals_rolling_max(self):
        rng = np.random.default_rng(88)
        dr = rng.normal(0, 0.01, 100)
        me = max_effect(dr, window=20)
        # Manually verify last entry
        assert me[-1] == pytest.approx(dr[-20:].max(), rel=1e-9)

    def test_output_length(self):
        dr = np.arange(0.0, 40.0)
        assert len(max_effect(dr, window=10)) == len(dr)
