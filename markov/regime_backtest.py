"""Backtest WALK-FORWARD al semnalului de regim Markov: la fiecare pas re-estimeaza
matricea de tranzitie DOAR din trecut (fara look-ahead), ia semnalul
P(BULL|azi) - P(BEAR|azi), pozitia = semnul lui, si scoreaza randamentul de maine.
Raporteaza Sharpe anualizat + max drawdown.

ATENTIE: metoda Markov bull/sideways/bear NU a produs edge tradabil pe activele
testate in proiect (results/REPORT.md). NU consiliere de investitii.
"""

import numpy as np

from markov.backtest import walk_forward
from markov.states import State, classify_states
from markov.transition import transition_matrix


def markov_signal(past_prices, window=20, threshold=0.05):
    """Pozitia tinta in {-1, 0, +1} din regimul Markov estimat DOAR pe `past_prices`.
    +1 daca P(BULL maine) > P(BEAR maine) pentru starea curenta, -1 invers, 0 neutru."""
    past = np.asarray(past_prices, dtype=float)
    if len(past) < window + 2:
        return 0.0
    states = classify_states(past, window=window, threshold=threshold)
    real = [s for s in states if s != State.UNKNOWN]
    if len(real) < 2:
        return 0.0
    cur = int(real[-1])
    P = transition_matrix(states)
    sig = P[cur, int(State.BULL)] - P[cur, int(State.BEAR)]
    return float(np.sign(sig))


def walk_forward_markov(prices, window=20, threshold=0.05, warmup=None, cost=0.0):
    """Ruleaza semnalul Markov prin backtest.walk_forward (expanding window, fara
    look-ahead). Intoarce {sharpe, max_drawdown, net_return, n_days}."""
    prices = np.asarray(prices, dtype=float)
    warmup = warmup if warmup is not None else max(window + 2, 60)
    if warmup >= len(prices) - 1:
        return {"sharpe": float("nan"), "max_drawdown": float("nan"),
                "net_return": float("nan"), "n_days": 0}
    res = walk_forward(prices, lambda past: markov_signal(past, window, threshold),
                       warmup=warmup, cost=cost)
    n = len(prices)
    fwd = prices[warmup + 1:n] / prices[warmup:n - 1] - 1.0
    daily = res["positions"] * fwd
    sd = daily.std(ddof=0)
    sharpe = float(daily.mean() / sd * np.sqrt(252)) if sd > 0 else float("nan")
    eq = np.cumprod(1.0 + daily)
    mdd = (float(((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min())
           if len(eq) else float("nan"))
    return {"sharpe": sharpe, "max_drawdown": mdd,
            "net_return": res["net_return"], "n_days": res["n_days"]}
