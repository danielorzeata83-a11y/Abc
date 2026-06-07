"""Monitor DESCRIPTIV de watchlist pentru regula validata 'dip adanc': pentru
fiecare nume arata cat e sub maximul recent (drawdown), daca a intrat in zona de
dip adanc (-`dip`), cat mai are pana acolo, si daca e peste MA scurta (semn de
redresare). NU da semnal de cumparare -- e o harta, nu un buton.

Reaminteste: pe BTC (test prin crize) regula a fost o FRANA DE RISC (drawdown -25%
vs -77% buy-and-hold), nu un accelerator de profit; pe petrol a fost neprofitabila.
Vezi results/BEARTEST_FINDINGS.md. NU consiliere de investitii.
"""

import numpy as np

from markov.dipbuy import drawdown, rolling_high
from markov.trendpull import ma


def dip_status(close, lookback=60, dip=0.4, exit_ma=20):
    """Snapshot al regulii dip-adanc pentru ultima bara. Descriptiv."""
    close = np.asarray(close, dtype=float)
    rh = rolling_high(close, lookback)
    dd = drawdown(close, lookback)
    ma_s = ma(close, exit_ma)
    price, high, cur_dd = float(close[-1]), float(rh[-1]), float(dd[-1])
    in_deep = np.isfinite(cur_dd) and cur_dd <= -dip
    trigger_price = high * (1.0 - dip)                  # pretul la care dd = -dip
    to_threshold = (trigger_price / price - 1.0) if (price > 0 and not in_deep) else 0.0
    above_exit = np.isfinite(ma_s[-1]) and price > ma_s[-1]

    if not np.isfinite(cur_dd):
        label = "date insuficiente"
    elif cur_dd >= -0.05:
        label = "aproape de maxim"
    elif not in_deep:
        label = f"corectie {cur_dd*100:.0f}% (inca nu e dip adanc)"
    elif not above_exit:
        label = f"DIP ADANC {cur_dd*100:.0f}% -- zona regulii, inca sub MA"
    else:
        label = f"dip adanc {cur_dd*100:.0f}%, dar peste MA (redresare)"

    return {
        "price": price, "high": high, "drawdown": cur_dd,
        "in_deep_dip": bool(in_deep), "to_threshold": float(to_threshold),
        "above_exit_ma": bool(above_exit), "label": label,
    }
