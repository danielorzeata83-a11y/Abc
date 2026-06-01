"""Tests for the trading-feasibility calculator.

Given position size, round-trip cost and a target net profit per trade,
work out the gross % move required, and given a realistic per-trade edge,
the capital needed to hit an annual profit goal.
"""

import pytest
from markov.feasibility import required_gross_move, capital_for_goal, expectancy_eur


def test_required_gross_move_adds_cost():
    # net target 10 EUR on 50 EUR position = 20% net; +1% round-trip cost.
    pct = required_gross_move(position=50, target_net=10, roundtrip_cost=0.01)
    assert pct == pytest.approx(0.21, abs=1e-6)  # 20% + 1%


def test_expectancy_eur_subtracts_cost():
    # 0.5% gross edge per trade on 1000 EUR, 0.1% cost -> 0.4% net = 4 EUR
    e = expectancy_eur(position=1000, edge_pct=0.005, roundtrip_cost=0.001)
    assert e == pytest.approx(4.0, abs=1e-6)


def test_expectancy_can_be_negative():
    assert expectancy_eur(position=50, edge_pct=0.002, roundtrip_cost=0.01) < 0


def test_capital_for_goal_scales_inversely_with_edge():
    # Need annual 5000 EUR, 1000 trades, net edge 0.4% per trade.
    cap = capital_for_goal(annual_goal=5000, trades=1000, net_edge_pct=0.004)
    # profit = trades * net_edge_pct * capital  -> capital = goal/(t*edge)
    assert cap == pytest.approx(5000 / (1000 * 0.004), abs=1e-6)


def test_capital_for_goal_infinite_when_no_edge():
    assert capital_for_goal(5000, 1000, 0.0) == float("inf")
