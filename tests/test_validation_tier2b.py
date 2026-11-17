"""TIER 2b cross-sectional: loader panel, Sharpe, sign-flip p-value, evaluare."""

import numpy as np
import pandas as pd

from markov.validation import tier2b


def _panel_csv(tmp_path, T=220, N=12, seed=0):
    """CSV long sintetic (date, ohlcv, Name) pentru un univers mic."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=T)
    rows = []
    for j in range(N):
        close = 100 * np.cumprod(1 + rng.normal(0, 0.02, T))
        vol = rng.uniform(1e5, 1e6, T)
        for i, d in enumerate(dates):
            c = close[i]
            rows.append((d.strftime("%Y-%m-%d"), c, c + 1, c - 1, c, vol[i],
                         f"S{j:02d}"))
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close",
                                     "volume", "Name"])
    p = tmp_path / "uni.csv"
    df.to_csv(p, index=False)
    return str(p)


def test_load_universe_shapes_and_complete_panel(tmp_path):
    P, V, dates = tier2b.load_universe(_panel_csv(tmp_path, T=200, N=8))
    assert P.shape == (200, 8) and V.shape == (200, 8)
    assert len(dates) == 200 and np.isfinite(P).all()


def test_sharpe_sign_matches_drift():
    rng = np.random.default_rng(1)
    pos = 0.001 + rng.normal(0, 0.005, 500)      # drift pozitiv
    neg = -0.001 + rng.normal(0, 0.005, 500)
    assert tier2b.sharpe(pos) > 0 and tier2b.sharpe(neg) < 0


def test_signflip_pvalue_low_for_drift_high_for_noise():
    rng = np.random.default_rng(2)
    drift = 0.002 + rng.normal(0, 0.004, 800)    # edge clar
    noise = rng.normal(0, 0.01, 800)
    assert tier2b.signflip_pvalue(drift) < 0.05
    assert tier2b.signflip_pvalue(noise) > 0.10


def test_evaluate_factor_keys_and_oos_split():
    r = np.r_[np.full(60, 0.001), np.full(40, 0.002)]
    m = tier2b.evaluate_factor(r, split_frac=0.6, n_perm=500)
    assert set(m) == {"n_days", "sharpe_full", "sharpe_oos", "p_value_oos"}
    assert m["n_days"] == 100


def test_run_and_render_end_to_end(tmp_path):
    rows = tier2b.run_xs_validation(_panel_csv(tmp_path), n_perm=300)
    assert set(rows) == set(tier2b.FACTORS)
    txt = tier2b.render_xs(rows, n_assets=12)
    assert "TIER 2b" in txt and "Sharpe_OOS" in txt
    assert "consiliere de investi" in txt.lower()
    for name in tier2b.FACTORS:
        assert name in txt
