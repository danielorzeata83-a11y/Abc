"""Incarca o serie de pret single-column (CSV gen wti/brent/btc) intr-un Bars.
Doar close conteaza pentru sisteme close-only (ex. buy-the-dip); high/low/open
sunt setate = close. NU consiliere de investitii.
"""

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars


def load_price_series(csv, date_col, price_col):
    """CSV cu o coloana de data si una de pret -> Bars (open=high=low=close)."""
    d = pd.read_csv(csv)
    d = d[[date_col, price_col]].dropna()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna().sort_values(date_col)
    close = d[price_col].to_numpy(dtype=float)
    ts = d[date_col].to_numpy()
    vol = np.ones(len(close))
    return Bars(ts, close.copy(), close.copy(), close.copy(), close.copy(), vol)
