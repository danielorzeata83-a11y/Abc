"""Tests for the law-of-large-numbers edge demonstration."""

import pytest
from markov.lln import edge_per_bet, prob_profit, monte_carlo_prob_profit


def test_edge_per_bet_even_money():
    # 52% win rate, win=loss=1 -> expected +0.04 per bet
    assert edge_per_bet(0.52, 1.0, 1.0) == pytest.approx(0.04, abs=1e-9)


def test_edge_negative_when_below_half_even_money():
    assert edge_per_bet(0.48, 1.0, 1.0) < 0


def test_prob_profit_rises_with_number_of_bets():
    p1 = prob_profit(0.52, 1, 1.0, 1.0)
    p100 = prob_profit(0.52, 100, 1.0, 1.0)
    p10000 = prob_profit(0.52, 10000, 1.0, 1.0)
    assert p1 < p100 < p10000
    assert p1 == pytest.approx(0.52, abs=0.02)      # one bet ~ the win rate
    assert p10000 > 0.999                            # near-certain with many


def test_prob_profit_half_is_half():
    assert prob_profit(0.50, 1000, 1.0, 1.0) == pytest.approx(0.5, abs=1e-6)


def test_no_edge_never_becomes_profitable():
    # 50% stays 50% no matter how many bets -> LLN doesn't manufacture edge
    assert prob_profit(0.50, 100000, 1.0, 1.0) == pytest.approx(0.5, abs=1e-6)


def test_monte_carlo_agrees_with_analytic():
    mc = monte_carlo_prob_profit(0.55, 200, 1.0, 1.0, trials=4000, seed=0)
    an = prob_profit(0.55, 200, 1.0, 1.0)
    assert abs(mc - an) < 0.05
