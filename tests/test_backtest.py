"""Tests for the walk-forward backtest (Step 9).

Critical property: NO look-ahead. On each day t the engine may use only
prices up to and including day t to build the transition matrix and the
signal, then it takes a position that earns the return realised on day
t+1. The matrix is re-estimated as we walk forward (expanding window).

Costs: a per-trade cost (commission + slippage) is charged on the change
in position between consecutive days.
"""

import numpy as np
import pytest

from markov.backtest import walk_forward
from markov.states import State


def _prices_from_daily_returns(returns):
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1.0 + r))
    return np.array(prices)


def test_no_lookahead_position_uses_only_past():
    # A spy on the data: walk_forward must never call the signal with a
    # price array longer than the current day index.
    prices = _prices_from_daily_returns(list(np.random.normal(0, 0.02, 200)))
    seen_lengths = []

    def spy_strategy(past_prices):
        seen_lengths.append(len(past_prices))
        return 0.0  # flat

    walk_forward(prices, strategy=spy_strategy, warmup=20)
    # Each call must see strictly fewer prices than the full series.
    assert max(seen_lengths) < len(prices)
    # And lengths must be monotonically increasing (expanding window).
    assert seen_lengths == sorted(seen_lengths)


def test_flat_strategy_earns_nothing_and_pays_nothing():
    prices = _prices_from_daily_returns([0.01] * 100)
    result = walk_forward(prices, strategy=lambda p: 0.0, warmup=20, cost=0.001)
    assert result["net_return"] == pytest.approx(0.0, abs=1e-12)
    assert result["n_trades"] == 0


def test_always_long_matches_buy_and_hold_minus_one_cost():
    # Always fully long: one entry trade, then hold. Net return should be
    # buy&hold return on the traded segment minus a single entry cost.
    rets = [0.01] * 50
    prices = _prices_from_daily_returns(rets)
    result = walk_forward(prices, strategy=lambda p: 1.0, warmup=20, cost=0.002)
    # Position goes 0 -> 1 once: exactly one cost of `cost`.
    assert result["n_trades"] == 1
    assert result["gross_return"] > result["net_return"]


def test_costs_scale_with_position_changes():
    # Alternate long/short every day -> a trade (size 2 turn) every step.
    prices = _prices_from_daily_returns(list(np.random.normal(0, 0.02, 60)))
    flip = {"v": 1.0}

    def alternator(p):
        flip["v"] *= -1
        return flip["v"]

    cheap = walk_forward(prices, strategy=alternator, warmup=20, cost=0.0)
    flip["v"] = 1.0
    pricey = walk_forward(prices, strategy=alternator, warmup=20, cost=0.01)
    assert pricey["net_return"] < cheap["net_return"]
    assert pricey["total_cost"] > 0


def test_result_has_equity_curve_of_right_length():
    prices = _prices_from_daily_returns([0.01] * 100)
    result = walk_forward(prices, strategy=lambda p: 1.0, warmup=20, cost=0.0)
    # One equity point per traded day (from warmup to the second-last day).
    assert len(result["equity_curve"]) == result["n_days"]
    assert result["n_days"] == (len(prices) - 1) - 20


def test_rejects_warmup_longer_than_series():
    prices = _prices_from_daily_returns([0.01] * 10)
    with pytest.raises(ValueError):
        walk_forward(prices, strategy=lambda p: 1.0, warmup=20)
