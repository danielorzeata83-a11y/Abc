"""The CLI's ticker loader returns a sorted, ticker-filtered close series."""

import numpy as np
import pandas as pd

from trend_cli import load_ticker


def test_load_ticker_filters_and_sorts(tmp_path):
    csv = tmp_path / "panel.csv"
    pd.DataFrame({
        "date": ["2015-01-03", "2015-01-01", "2015-01-02", "2015-01-01"],
        "close": [12.0, 10.0, 11.0, 999.0],
        "Name": ["NVDA", "NVDA", "NVDA", "AAPL"],
    }).to_csv(csv, index=False)

    dates, close = load_ticker(str(csv), "NVDA")

    assert list(close) == [10.0, 11.0, 12.0]          # sorted by date, NVDA only
    assert list(dates) == ["2015-01-01", "2015-01-02", "2015-01-03"]
    assert isinstance(close, np.ndarray)
