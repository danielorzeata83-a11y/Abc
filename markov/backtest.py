"""Walk-forward backtest (Step 9).

The cardinal rule: no look-ahead. On each day t the strategy is shown
ONLY prices[:t+1] (an expanding window of the past) and returns a target
position in [-1, 1]. That position then earns the return realised over
the next day, return[t] = prices[t+1]/prices[t] - 1.

Transaction costs are charged on turnover -- the absolute change in
position between consecutive days -- modelling commission + slippage.
"""

import numpy as np


def walk_forward(prices, strategy, warmup=20, cost=0.0):
    """Run an expanding-window walk-forward backtest.

    Parameters
    ----------
    prices : array-like
        Price series of length N+1 (yields N daily returns).
    strategy : callable
        strategy(past_prices) -> target position in [-1, 1], where
        past_prices is prices[:t+1] (no future data).
    warmup : int
        Number of initial days skipped so the strategy has history.
    cost : float
        Per-unit-turnover cost (e.g. 0.001 = 10 bps round-trip per unit).

    Returns a dict with gross/net returns, total cost, trade count,
    per-day equity curve and the realised position/return series.
    """
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    if warmup >= n - 1:
        raise ValueError(f"warmup={warmup} too large for series of length {n}")

    gross_equity = 1.0
    net_equity = 1.0
    total_cost = 0.0
    n_trades = 0
    prev_pos = 0.0
    equity_curve = []
    positions = []

    # Day t earns return[t] = prices[t+1]/prices[t] - 1, using only the past.
    for t in range(warmup, n - 1):
        past = prices[: t + 1]
        pos = float(strategy(past))
        pos = max(-1.0, min(1.0, pos))  # clamp to [-1, 1]

        ret = prices[t + 1] / prices[t] - 1.0
        turnover = abs(pos - prev_pos)
        if turnover > 0:
            n_trades += 1
        day_cost = cost * turnover
        total_cost += day_cost

        gross_equity *= 1.0 + pos * ret
        net_equity *= 1.0 + pos * ret - day_cost

        equity_curve.append(net_equity)
        positions.append(pos)
        prev_pos = pos

    return {
        "gross_return": gross_equity - 1.0,
        "net_return": net_equity - 1.0,
        "total_cost": total_cost,
        "n_trades": n_trades,
        "n_days": len(equity_curve),
        "equity_curve": np.array(equity_curve),
        "positions": np.array(positions),
    }
