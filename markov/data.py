"""Price data loading for the Markov regime engine.

Reads a CSV with a date column and a price column, cleans it (drops
missing / non-positive prices), and returns a tidy DataFrame with
columns ["date", "price"] sorted ascending by date. This is the single
seam between any data source (GitHub CSV today, exchange API later) and
the rest of the engine.
"""

import pandas as pd


def load_prices(path, date_col="time", price_col="PriceUSD"):
    """Load and clean a price series from a CSV file.

    Returns a DataFrame with columns ["date", "price"], sorted by date,
    containing only rows with a valid (present, positive) price.
    """
    df = pd.read_csv(path, usecols=lambda c: c in (date_col, price_col))
    missing = {date_col, price_col} - set(df.columns)
    if missing:
        raise KeyError(f"missing required columns: {sorted(missing)}")

    df = df.rename(columns={date_col: "date", price_col: "price"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype(float)

    df = df.dropna(subset=["date", "price"])
    df = df[df["price"] > 0]
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "price"]]
