"""Law of large numbers: how a tiny per-bet edge becomes near-certain profit.

A 52% win rate is almost a coin flip on ONE bet. But across many
INDEPENDENT bets the outcomes average out and the probability of finishing
in profit climbs toward certainty -- the statistical engine behind "many
small uncorrelated edges" that real funds run. Crucially, this only works
if the bets are independent; one big bet (or many correlated ones) keeps
the coin-flip uncertainty. And it cannot manufacture an edge from nothing:
a 50% win rate stays 50% forever.

Not investment advice.
"""

import math
import random


def edge_per_bet(win_rate, win_amt, loss_amt):
    """Expected value of a single bet."""
    return win_rate * win_amt - (1.0 - win_rate) * loss_amt


def _phi(x):
    """Standard normal CDF via erf (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def prob_profit(win_rate, n, win_amt, loss_amt):
    """P(sum of n independent bets > 0), normal approximation."""
    mean = edge_per_bet(win_rate, win_amt, loss_amt)
    # variance of one bet
    e_x2 = win_rate * win_amt ** 2 + (1.0 - win_rate) * loss_amt ** 2
    var = e_x2 - mean ** 2
    if var <= 0:
        return 1.0 if mean > 0 else (0.5 if mean == 0 else 0.0)
    # P(sum>0) = Phi(n*mean / sqrt(n*var)) = Phi(sqrt(n)*mean/sd)
    z = math.sqrt(n) * mean / math.sqrt(var)
    return _phi(z)


def monte_carlo_prob_profit(win_rate, n, win_amt, loss_amt, trials=2000,
                            seed=0):
    """Empirical P(profit over n bets) by simulation -- sanity check."""
    rng = random.Random(seed)
    wins = 0
    for _ in range(trials):
        total = 0.0
        for _ in range(n):
            total += win_amt if rng.random() < win_rate else -loss_amt
        if total > 0:
            wins += 1
    return wins / trials
