"""Metrici de TRADER pentru o serie de pozitii cauzale -- ce conta cu adevarat
cand scopul e "tranzactii cu profit", nu "bate buy-and-hold":

- n_trades, win_rate, profit_factor (suma castiguri / suma pierderi),
- avg_win, avg_loss, expectancy (castig mediu pe tranzactie, net de cost),
- net_return si max_drawdown pe curba de capital.

p-value (din posscore) ramane GARDA de onestitate: profitul e timing real sau
doar drift de piata? NU consiliere de investitii.
"""

import numpy as np


def trade_stats(positions, fwd, cost=0.0005):
    """positions (0/1) tinute peste fwd[t]. Segmenteaza in tranzactii (runuri de
    pozitie>0), calculeaza randamentul fiecareia net de cost dus-intors (2*cost),
    plus win-rate / profit-factor / expectancy si max drawdown pe capital net."""
    positions = np.asarray(positions, dtype=float)
    fwd = np.asarray(fwd, dtype=float)
    n = len(positions)

    trades, i = [], 0
    while i < n:
        if positions[i] > 0:
            j = i
            while j < n and positions[j] > 0:
                j += 1
            trades.append(float(np.prod(1.0 + fwd[i:j]) - 1.0 - 2.0 * cost))
            i = j
        else:
            i += 1
    trades = np.array(trades, dtype=float)

    turnover = np.abs(np.diff(np.concatenate([[0.0], positions])))
    net_daily = positions * fwd - cost * turnover
    eq = np.cumprod(1.0 + net_daily)
    mdd = (float((eq / np.maximum.accumulate(eq) - 1.0).min())
           if len(eq) else float("nan"))
    net_return = float(eq[-1] - 1.0) if len(eq) else 0.0

    if len(trades) == 0:
        return {"n_trades": 0, "win_rate": float("nan"),
                "profit_factor": float("nan"), "avg_win": float("nan"),
                "avg_loss": float("nan"), "expectancy": float("nan"),
                "net_return": net_return, "max_drawdown": mdd}

    wins = trades[trades > 0]
    losses = trades[trades <= 0]
    pf = float(wins.sum() / abs(losses.sum())) if losses.sum() < 0 else float("inf")
    return {
        "n_trades": int(len(trades)),
        "win_rate": float(len(wins) / len(trades)),
        "profit_factor": pf,
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "expectancy": float(trades.mean()),
        "net_return": net_return,
        "max_drawdown": mdd,
    }
