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

DISCLAIMER = "NU este consiliere de investitii. Artefact descriptiv -- NU semnal."


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


def dip_alert(items, asof="", lookback=60, dip=0.4, exit_ma=20, near=0.05):
    """Construieste alerta LINISTITA: listeaza doar numele in zona de dip adanc
    sau aproape de prag (in `near`). `active` e False cand nu e nimic de raportat
    (ca alerta sa nu spameze zilnic). items: list[(nume, close_array)].

    Intoarce {"text": str, "active": bool}. Descriptiv, NU semnal de cumparare.
    """
    deep, close_to = [], []
    for name, close in items:
        if close is None or len(close) < lookback + 2:
            continue
        s = dip_status(close, lookback=lookback, dip=dip, exit_ma=exit_ma)
        if s["in_deep_dip"]:
            deep.append((name, s))
        elif -near <= s["to_threshold"] < 0:
            close_to.append((name, s))

    L = [f"Abc -- alerta dip-adanc {asof}".strip(),
         f"(prag {dip*100:.0f}% sub maximul a {lookback} zile)", ""]
    if deep:
        L.append("IN ZONA DE DIP ADANC:")
        for name, s in deep:
            ma_tag = "peste MA (redresare?)" if s["above_exit_ma"] else "inca sub MA"
            L.append(f"  {name}: {s['drawdown']*100:.0f}% sub maxim -- {ma_tag}")
    if close_to:
        L.append("" if deep else "")
        L.append("APROAPE de prag:")
        for name, s in close_to:
            L.append(f"  {name}: {s['drawdown']*100:.0f}% sub maxim, "
                     f"mai cade {abs(s['to_threshold'])*100:.0f}% pana la prag")
    if not deep and not close_to:
        L.append("Nimic in zona de dip adanc azi.")
    L += ["",
          "Reaminteste: regula a fost FRANA DE RISC (drawdown injumatatit in crize),",
          "nu accelerator de profit. Tu decizi.", "", DISCLAIMER]
    return {"text": "\n".join(L), "active": bool(deep or close_to)}
