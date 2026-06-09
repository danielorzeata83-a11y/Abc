"""TIER 2b pe istoric lung din cache: panel_from_cache + ruta --cache-dir."""

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.validation import tier2b
import validate_xs_cli


def _seed(data_dir, symbol, start, n, seed):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.02, n))
    write_bars(data_dir, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    rng.uniform(1e5, 1e6, n)))


def test_list_cache_symbols(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA", "2010-01-04", 300, 0)
    _seed(d, "BBB", "2010-01-04", 300, 1)
    assert tier2b.list_cache_symbols(d) == ["AAA", "BBB"]


def test_panel_from_cache_common_window(tmp_path):
    d = str(tmp_path)
    # AAA istoric lung, BBB incepe mai tarziu -> fereastra comuna = a lui BBB
    _seed(d, "AAA", "2008-01-02", 800, 0)
    _seed(d, "BBB", "2010-01-04", 500, 1)
    P, V, dates, names = tier2b.panel_from_cache(d)
    assert names == ["AAA", "BBB"]
    assert P.shape[1] == 2 and V.shape == P.shape
    assert np.isfinite(P).all()                      # panel complet, fara goluri
    assert pd.Timestamp(dates[0]) >= pd.Timestamp("2010-01-04")


def test_panel_from_cache_needs_two_symbols(tmp_path):
    d = str(tmp_path)
    _seed(d, "AAA", "2010-01-04", 300, 0)
    try:
        tier2b.panel_from_cache(d)
        assert False, "ar fi trebuit sa ridice"
    except ValueError:
        pass


def test_cli_cache_dir_path(tmp_path, capsys):
    d = str(tmp_path)
    for i, s in enumerate(["AAA", "BBB", "CCC", "DDD"]):
        _seed(d, s, "2010-01-04", 320, i)
    validate_xs_cli.main(["--cache-dir", d, "--n-perm", "200"])
    out = capsys.readouterr().out
    assert "panel din cache: 4 nume" in out
    assert "TIER 2b" in out and "BLEND OOS" in out
    assert "consiliere de investi" in out.lower()
