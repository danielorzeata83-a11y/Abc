"""CLI #3: cache din CSV long + pooling IC pe univers larg."""

import numpy as np
import pandas as pd

import validate_universe_cli as vu


def _panel_csv(tmp_path, T=260, N=20, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=T)
    rows = []
    for j in range(N):
        close = 100 * np.cumprod(1 + rng.normal(0, 0.02, T))
        for i, d in enumerate(dates):
            c = close[i]
            rows.append((d.strftime("%Y-%m-%d"), c, c + 1, c - 1, c,
                         rng.uniform(1e5, 1e6), f"S{j:02d}"))
    p = tmp_path / "uni.csv"
    pd.DataFrame(rows, columns=["date", "open", "high", "low", "close",
                                "volume", "Name"]).to_csv(p, index=False)
    return str(p)


def test_cache_from_long_csv_writes_and_filters(tmp_path):
    csv = _panel_csv(tmp_path, T=260, N=5)
    cache = tmp_path / "cache"
    syms = vu.cache_from_long_csv(csv, str(cache), min_obs=200)
    assert len(syms) == 5
    # nume cu prea putine bare e filtrat
    short = vu.cache_from_long_csv(csv, str(cache), min_obs=10_000)
    assert short == []


def test_cli_pools_over_universe(tmp_path, capsys):
    csv = _panel_csv(tmp_path, T=260, N=20)
    vu.main(["--universe", csv, "--indicators", "tier2", "--horizons", "1,5"])
    out = capsys.readouterr().out
    assert "univers: 20 simboluri" in out
    assert "ts_momentum" in out and "consiliere de investi" in out.lower()
