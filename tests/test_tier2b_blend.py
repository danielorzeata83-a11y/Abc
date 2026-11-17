"""Blend sign-aware (conviction) al factorilor cross-sectionali."""

import numpy as np

from markov.validation import tier2b


def test_align_right_aligns_to_common_tail():
    streams = {"a": np.arange(10.0), "b": np.arange(7.0) + 100}
    names, M = tier2b.align_streams(streams)
    assert M.shape == (7, 2)
    # coada comuna: ultimele 7 din 'a' (3..9) si tot 'b'
    assert np.allclose(M[:, 0], np.arange(3, 10))
    assert np.allclose(M[:, 1], np.arange(7) + 100)


def test_blend_zero_weight_on_negative_insample():
    rng = np.random.default_rng(0)
    n = 500
    good = 0.001 + rng.normal(0, 0.004, n)     # Sharpe in-sample pozitiv
    bad = -0.001 + rng.normal(0, 0.004, n)     # negativ -> pondere 0
    b = tier2b.blend_oos({"good": good, "bad": bad}, n_perm=300)
    assert b["weights"]["good"] > 0.99 and b["weights"]["bad"] == 0.0


def test_blend_positive_factor_carries_oos():
    rng = np.random.default_rng(1)
    n = 600
    good = 0.0015 + rng.normal(0, 0.004, n)
    noise = rng.normal(0, 0.004, n)
    b = tier2b.blend_oos({"good": good, "noise": noise}, n_perm=500)
    assert b["sharpe_oos"] > 0
    assert b["weights"]["good"] >= b["weights"]["noise"]


def test_blend_all_negative_is_flat():
    rng = np.random.default_rng(2)
    a = -0.002 + rng.normal(0, 0.003, 400)
    c = -0.001 + rng.normal(0, 0.003, 400)
    b = tier2b.blend_oos({"a": a, "c": c}, n_perm=200)
    assert all(w == 0.0 for w in b["weights"].values())
    assert b["sharpe_oos"] != b["sharpe_oos"] or b["sharpe_oos"] == 0  # nan sau 0 (flat)


def test_render_blend_has_disclaimer_and_factors():
    rng = np.random.default_rng(3)
    b = tier2b.blend_oos({"x": 0.001 + rng.normal(0, 0.003, 300),
                          "y": rng.normal(0, 0.003, 300)}, n_perm=200)
    txt = tier2b.render_blend(b)
    assert "Blend sign-aware" in txt and "BLEND OOS" in txt
    assert "consiliere de investi" in txt.lower()
    assert "x" in txt and "y" in txt
