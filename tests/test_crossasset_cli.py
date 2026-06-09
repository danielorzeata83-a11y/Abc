import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
import crossasset_cli


def _seed_daily(dirpath, symbol, rets):
    n = len(rets) + 1
    idx = pd.bdate_range("2010-01-04", periods=n)
    close = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + rets)))
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), close, close + 1, close - 1, close,
                    np.full(n, 1e6)))


def test_cli_prints_network(tmp_path, capsys):
    d = str(tmp_path)
    rng = np.random.default_rng(0)
    for s in ("AAA", "BBB"):
        _seed_daily(d, s, rng.normal(0, 0.01, size=600))
    crossasset_cli.main(["--symbols", "AAA,BBB", "--data-dir", d])
    out = capsys.readouterr().out.lower()
    assert "consiliere de investi" in out
    assert "lead-lag" in out and "zile comune" in out
