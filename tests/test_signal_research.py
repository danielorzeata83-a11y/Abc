import numpy as np
import pytest

from sensa.signal_research import ForwardReturns, evaluate_signal, evidence_weights, spearman, verdict


def test_spearman_rank_correlation_with_ties():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    assert spearman([1, 1, 1, 1], [1, 2, 3, 4]) is None                       # a constant signal has no rank information
    assert abs(spearman([1, 2, 3, 4, 5, 6], [2, 1, 4, 3, 6, 5])) < 1.0 and spearman([1, 2], [1, 2]) is None            # too few points


def test_forward_returns_start_at_the_first_close_on_or_after_the_date_and_look_h_trading_days_ahead():
    dates = [f"2026-01-{d:02d}" for d in range(1, 11)]
    closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109.0]
    fr = ForwardReturns(lambda t: (dates, closes) if t == "A" else None)
    assert fr.ret("A", "2026-01-03", 2) == pytest.approx(104 / 102 - 1)
    assert fr.ret("A", "2025-12-30", 1) == pytest.approx(101 / 100 - 1)              # a couple of days before the series: first close
    assert fr.ret("A", "2026-01-09", 5) is None and fr.ret("B", "2026-01-03", 1) is None


def dated_samples(n_dates=12, n=40, strength=0.5, seed=0):
    """signal that predicts the forward return with a given strength"""
    rng = np.random.default_rng(seed)
    out = {}
    for d in range(n_dates):
        sig = rng.normal(size=n)
        noise = rng.normal(size=n)
        r = 0.02 * (strength * sig + (1 - strength) * noise)
        out[f"2024-{d + 1:02d}-15"] = [{"ticker": f"T{i}", "value": float(sig[i]), "fwd": {21: float(r[i])}} for i in range(n)]
    return out


def test_a_real_signal_shows_a_positive_information_coefficient_and_a_top_group_edge():
    st = evaluate_signal(dated_samples(strength=0.7), horizons=(21,))[21]
    assert st["n_dates"] == 12 and st["mean_ic"] > 0.3 and st["ic_t"] > 3 and st["ic_hit_pct"] > 80
    assert st["top_quintile_excess_pct"] > 0 and st["top10_excess_pct"] > 0
    assert verdict(st) == "works"


def test_a_useless_signal_is_not_proven_and_an_inverted_one_is_negative():
    none = evaluate_signal(dated_samples(strength=0.0, seed=3), horizons=(21,))[21]
    assert abs(none["ic_t"]) < 2.5 and verdict(none) in ("not_proven", "works", "negative")
    inv = evaluate_signal({d: [{**s, "value": -s["value"]} for s in v] for d, v in dated_samples(strength=0.7).items()}, horizons=(21,))[21]
    assert inv["mean_ic"] < 0 and verdict(inv) == "negative"


def test_dates_with_too_few_names_or_missing_returns_are_skipped_and_few_dates_means_too_little_data():
    s = dated_samples(n_dates=3)
    s["2025-01-15"] = s["2024-01-15"][:5]                                              # only 5 names: skipped
    st = evaluate_signal(s, horizons=(21,), min_names=20)[21]
    assert st["n_dates"] == 3 and verdict(st) == "too_little_data"
    assert evaluate_signal({}, horizons=(21,))[21]["n_dates"] == 0


def test_evidence_weights_only_turn_down_unproven_signals_boost_strong_ones_and_keep_untested_ones():
    defaults = {"momentum": 0.25, "smart": 0.30, "insider": 0.15, "politician": 0.05, "quality": 0.15, "trend": 0.10}
    evidence = {"momentum_12_1": {"verdict": "works", "mean_ic": 0.05, "ic_t": 3.5, "n_dates": 20},
                "smart_money": {"verdict": "not_proven", "mean_ic": 0.01, "ic_t": 0.6, "n_dates": 8},
                "insider_net": {"verdict": "negative", "mean_ic": -0.04, "ic_t": -2.5, "n_dates": 20}}
    mapping = {"momentum_12_1": "momentum", "smart_money": "smart", "insider_net": "insider"}
    w = evidence_weights(evidence, defaults, mapping)
    assert w["insider"] == 0 and w["politician"] > 0 and w["trend"] > 0                 # untested stay in
    assert w["momentum"] / w["smart"] > 0.25 / 0.30                                    # the proven one gained against the unproven one
    assert sum(w.values()) == pytest.approx(sum(defaults.values()))
    assert evidence_weights({}, defaults, mapping) == defaults
