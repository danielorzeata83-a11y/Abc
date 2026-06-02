"""Dollar-cost-averaging (DCA) buy & hold simulator.

The realistic retail implementation of "many small uncorrelated bets": buy
a fixed amount of a diversified index every period and hold. Each period
buys `contribution / price` units; the units accumulate and the final value
is units * last price. DCA automatically buys more when cheap and less when
dear. Not investment advice.
"""

import numpy as np


def dca_simulate(prices, contribution):
    """Simulate investing `contribution` each period into `prices`.

    Returns total invested, units accumulated, value path, final value,
    profit and total return.
    """
    prices = np.asarray(prices, dtype=float)
    units_each = contribution / prices
    units_cum = np.cumsum(units_each)
    value_path = units_cum * prices
    invested = contribution * len(prices)
    final = float(value_path[-1])
    return {
        "total_invested": float(invested),
        "units": float(units_cum[-1]),
        "value_path": value_path,
        "final_value": final,
        "profit": final - invested,
        "return_pct": final / invested - 1.0 if invested else 0.0,
    }


def cagr(start_value, end_value, years):
    """Compound annual growth rate."""
    if start_value <= 0 or years <= 0:
        return 0.0
    return (end_value / start_value) ** (1.0 / years) - 1.0


def max_drawdown(values):
    """Largest peak-to-trough fractional decline of a value series."""
    values = np.asarray(values, dtype=float)
    peak = np.maximum.accumulate(values)
    return float(((values - peak) / peak).min())


def project_dca(monthly, years, annual_return):
    """Project a monthly DCA plan forward at a constant annual return.

    Contributions are made at the end of each month and compounded at the
    monthly equivalent of `annual_return`. Returns invested, final value and
    profit. A projection, not a promise -- real returns vary widely.
    """
    n = int(round(years * 12))
    i = (1 + annual_return) ** (1 / 12) - 1
    value = 0.0
    for _ in range(n):
        value = value * (1 + i) + monthly
    invested = monthly * n
    return {"invested": invested, "final_value": value,
            "profit": value - invested, "months": n}
