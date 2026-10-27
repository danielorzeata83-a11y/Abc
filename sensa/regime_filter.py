"""Market regime from the S&P 500 and an honest test of whether stepping aside in bad regimes would have helped.

The label uses three plain facts: price against its 200-day average, the fall from the 52-week high and how high the
recent volatility is compared with the last year. The backtest applies one a-priori rule (hold only while the index is
above its 200-day average, otherwise cash) and reports the result whichever way it goes; nothing is tuned."""

import numpy as np
import pandas as pd

from sensa.lab_backtest import metrics

WINDOW = 200


def _series(closes):
    c = np.asarray(closes, dtype=float)
    n = len(c)
    ma = np.full(n, np.nan)
    dd = np.full(n, np.nan)
    vol = np.full(n, np.nan)
    r = np.concatenate([[np.nan], c[1:] / c[:-1] - 1])
    for t in range(n):
        if t >= WINDOW - 1:
            ma[t] = c[t - WINDOW + 1:t + 1].mean()
        if t >= 251:
            dd[t] = c[t] / c[t - 251:t + 1].max() - 1
        if t >= 20:
            vol[t] = r[t - 19:t + 1].std(ddof=1) * np.sqrt(252)
    pct = np.full(n, np.nan)
    for t in range(251, n):
        w = vol[max(20, t - 251):t + 1]
        pct[t] = float((w <= vol[t]).mean())
    return c, ma, dd, vol, pct


def regime_labels(closes):
    c, ma, dd, vol, pct = _series(closes)
    out = []
    for t in range(len(c)):
        if np.isnan(dd[t]) or np.isnan(ma[t]):
            out.append(None)
            continue
        below, deep, volhi = c[t] < ma[t], dd[t] <= -0.10, pct[t] >= 0.9
        out.append("risk_off" if below and deep else "caution" if below or deep or volhi else "risk_on")
    return out


def current_regime(closes, dates):
    labels = regime_labels(closes)
    if not labels or labels[-1] is None:
        return None
    c, ma, dd, vol, pct = _series(closes)
    i = len(c) - 1
    j = i
    while j > 0 and labels[j - 1] == labels[i]:
        j -= 1
    spy = {"price": float(c[i]), "ma200": float(ma[i]), "pct_vs_ma200": float((c[i] / ma[i] - 1) * 100), "drawdown_pct": float(dd[i] * 100),
           "vol_1m_pct": float(vol[i] * 100), "vol_percentile": float(pct[i])}
    reasons = [f"The S&P 500 is {abs(spy['pct_vs_ma200']):.1f}% {'above' if spy['pct_vs_ma200'] >= 0 else 'below'} its 200-day average",
               f"It is {abs(spy['drawdown_pct']):.1f}% below its 52-week high" if spy["drawdown_pct"] < -0.05 else "It is at its 52-week high",
               f"Recent volatility is higher than on {spy['vol_percentile'] * 100:.0f}% of days in the last year"]
    advice = {"risk_on": "Trend and volatility are normal: momentum-based picks have their usual footing.",
              "caution": "One warning sign is on: keep new positions smaller and check the evidence below.",
              "risk_off": "The index is below its long-term average and well off its high: momentum signals are less reliable in such phases."}[labels[i]]
    return {"label": labels[i], "as_of": dates[i], "since": dates[j], "spy": spy, "reasons": reasons, "advice": advice}


def gate_backtest(closes, dates, window=WINDOW):
    c = np.asarray(closes, dtype=float)
    r = c[1:] / c[:-1] - 1
    pos = np.zeros(len(r))
    for t in range(window, len(r)):
        pos[t] = 1.0 if c[t] > c[t - window + 1:t + 1].mean() else 0.0        # decided on the close of day t, earns day t+1
    start = window
    idx = dates[1:][start:]
    gate = pd.Series(pos[start:] * r[start:], index=idx)
    hold = pd.Series(r[start:], index=idx)
    g, b = metrics(gate), metrics(hold)
    years = len(idx) / 252
    better_dd = g["max_drawdown"] - b["max_drawdown"]
    sg, sb = g["sharpe"] or 0.0, b["sharpe"] or 0.0
    if sg >= sb and better_dd >= 0.05:
        verdict, text = "helped", (f"Over the past {years:.0f} years, stepping aside below the 200-day average cut the worst fall from {b['max_drawdown'] * 100:.0f}% to "
                                   f"{g['max_drawdown'] * 100:.0f}% and kept the Sharpe ratio at {sg:.2f} (buy-and-hold {sb:.2f}).")
    elif sg < sb and g["ann_return"] < b["ann_return"] and better_dd < 0.05:
        verdict, text = "did_not_help", (f"Over the past {years:.0f} years, stepping aside did not help: Sharpe {sg:.2f} vs {sb:.2f} for buy-and-hold, "
                                         f"{g['ann_return'] * 100:.1f}% vs {b['ann_return'] * 100:.1f}% a year.")
    else:
        verdict, text = "mixed", (f"Over the past {years:.0f} years the result is mixed: worst fall {g['max_drawdown'] * 100:.0f}% vs {b['max_drawdown'] * 100:.0f}%, "
                                  f"Sharpe {sg:.2f} vs {sb:.2f}, return {g['ann_return'] * 100:.1f}% vs {b['ann_return'] * 100:.1f}% a year (no clear winner).")
    return {"window": window, "days": len(idx), "gate": {k: (None if v is None else float(v)) for k, v in g.items() if k != "days"},
            "buy_hold": {k: (None if v is None else float(v)) for k, v in b.items() if k != "days"},
            "time_in_market_pct": float(pos[start:].mean() * 100), "verdict": verdict, "verdict_text": text}
