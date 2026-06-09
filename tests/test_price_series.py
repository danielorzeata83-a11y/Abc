"""Loader serie de pret single-column -> Bars."""

import numpy as np
import pandas as pd

from markov.intraday.price_series import load_price_series


def test_loads_sorted_close_from_two_columns(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"Date": ["2020-01-03", "2020-01-02", "2020-01-04"],
                  "Price": [11.0, 10.0, 12.0]}).to_csv(csv, index=False)
    b = load_price_series(str(csv), "Date", "Price")
    assert list(b.close) == [10.0, 11.0, 12.0]              # sortat crescator
    assert np.array_equal(b.high, b.close) and np.array_equal(b.low, b.close)
