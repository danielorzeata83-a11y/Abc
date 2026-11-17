"""Raport de regim de piata pentru un simbol, din uneltele proiectului:
- stari Markov BULL/SIDEWAYS/BEAR (states + matrice de tranzitie + forecast),
- regim Hurst trend vs mean-revert (validation/regime),
- semnal de volatilitate (z realized_var, alert).

Date REALE din: --data-dir (cache daily backfilled) sau --universe (CSV long OHLCV).

    python .claude/skills/markov-regime/scripts/regime.py --symbol AAPL --universe data/sp500.csv
    python .claude/skills/markov-regime/scripts/regime.py --symbol NVDA --data-dir data/intraday

ATENTIE: metoda Markov bull/sideways/bear NU a produs edge tradabil pe niciun activ
testat in proiect (vezi results/REPORT.md). Acest raport e DESCRIPTIV. NU consiliere
de investitii.
"""

import argparse
import sys
from pathlib import Path

# Skill project-level: adauga radacina repo-ului pe sys.path ca importurile markov.*
# sa mearga indiferent de directorul din care e rulat scriptul.
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import numpy as np
import pandas as pd

from markov.intraday.cache import read_bars
from markov.regime_backtest import walk_forward_markov
from markov.states import State, classify_states, daily_returns
from markov.transition import forecast, stationary_distribution, transition_matrix
from markov.validation.regime import hurst_regime
from markov.validation.tier1 import INDICATORS
from markov.validation.ensemble import zscore_causal

_NAME = {int(State.BEAR): "BEAR", int(State.SIDEWAYS): "SIDEWAYS", int(State.BULL): "BULL"}
DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare descriptiv."


def _load_close(symbol, data_dir, universe):
    """(dates, close, bars-or-None) din cache sau CSV long. close = ndarray float."""
    if universe:
        raw = pd.read_csv(universe)
        g = raw[raw["Name"].astype(str) == str(symbol)].sort_values("date")
        if g.empty:
            raise SystemExit(f"{symbol} lipseste in {universe}")
        return (pd.to_datetime(g["date"]).to_numpy(),
                g["close"].to_numpy(dtype=float), None)
    bars = read_bars(data_dir, symbol)
    if bars is None:
        raise SystemExit(f"{symbol} lipseste in cache {data_dir} (ruleaza backfill_cli).")
    return bars.timestamps, np.asarray(bars.close, dtype=float), bars


def _hmm_section(close, n_states=3):
    """Strat HMM optional (hmmlearn). Degradare curata daca lipseste/da eroare:
    intoarce o lista de linii (goala daca nu e disponibil)."""
    try:
        import logging
        logging.getLogger("hmmlearn").setLevel(logging.ERROR)  # taci convergenta noisy
        from markov.hmm import hmm_states
    except Exception:
        return ["HMM: indisponibil (hmmlearn neinstalat) -- model observabil ruleaza normal."]
    try:
        states = hmm_states(close, n_states=n_states, seed=42)
        rets = daily_returns(close)
        m = min(len(states), len(rets))
        states, rets = np.asarray(states[:m]), np.asarray(rets[:m])
        means = [(k, float(rets[states == k].mean()) if np.any(states == k) else float("nan"))
                 for k in range(n_states)]
        means.sort(key=lambda kv: (np.isfinite(kv[1]), kv[1]))
        lab = ["BEAR (cea mai mica medie)", "SIDEWAYS", "BULL (cea mai mare medie)"]
        out = ["HMM (Baum-Welch + Viterbi) -- randament mediu zilnic per stare:"]
        for (k, mu), name in zip(means, lab):
            out.append(f"  {name:<26} stare {k}: {mu*100:+.3f}%/zi")
        out.append("  Nota: Baum-Welch are optime locale; in productie ruleaza mai multe seed-uri.")
        return out
    except Exception as exc:
        return [f"HMM: sarit la rulare ({exc})."]


def regime_report(symbol, dates, close, bars, window=20, threshold=0.05, horizon=5,
                  backtest=True, hmm=True):
    states = classify_states(close, window=window, threshold=threshold)
    real = [s for s in states if s != State.UNKNOWN]
    cur = int(real[-1]) if real else None
    P = transition_matrix(states)
    nxt = P[cur] if cur is not None else None
    P_h = forecast(P, horizon)
    pi = stationary_distribution(P)
    hl = hurst_regime(close)
    hcur = next((x for x in hl[::-1] if x != "na"), "na")
    volz = None
    if bars is not None:
        z = zscore_causal(np.asarray(INDICATORS["realized_var"](bars), dtype=float))
        fin = z[np.isfinite(z)]
        volz = float(fin[-1]) if len(fin) else None

    L = [DISCLAIMER, "", f"=== Regim de piata: {symbol} ===",
         f"date: {str(np.datetime_as_string(dates[0], unit='D'))}"
         f" .. {str(np.datetime_as_string(dates[-1], unit='D'))}  ({len(close)} bare)", ""]
    L.append(f"STARE MARKOV curenta: {_NAME.get(cur, 'N/A')}")
    if nxt is not None:
        L.append("  P(maine|azi):   " + "  ".join(
            f"{_NAME[j]}={nxt[j]:.2f}" for j in range(3)))
        L.append(f"  P({horizon} zile|azi): " + "  ".join(
            f"{_NAME[j]}={P_h[cur][j]:.2f}" for j in range(3)))
    L.append("  stationar:      " + "  ".join(f"{_NAME[j]}={pi[j]:.2f}" for j in range(3)))
    L.append("")
    L.append(f"REGIM HURST: {hcur}  (trend = momentum; meanrev = reversal)")
    if volz is not None:
        tag = "RIDICATA" if volz >= 1 else "SCAZUTA" if volz <= -1 else "normala"
        L.append(f"VOLATILITATE: z realized_var = {volz:+.2f}  ({tag})")
    if backtest:
        bt = walk_forward_markov(close, window=window, threshold=threshold)
        L += ["", "BACKTEST WALK-FORWARD (semn P(BULL)-P(BEAR), re-estimat la fiecare pas):"]
        if bt["n_days"]:
            sh = f"{bt['sharpe']:+.2f}" if np.isfinite(bt["sharpe"]) else "n/a"
            L.append(f"  Sharpe={sh}  maxDD={bt['max_drawdown']*100:.0f}%  "
                     f"net={bt['net_return']*100:+.0f}%  zile={bt['n_days']}")
            L.append("  (Reaminte: metoda Markov nu a aratat edge tradabil -- vezi REPORT.md.)")
        else:
            L.append("  serie prea scurta pentru backtest.")
    if hmm:
        L += [""] + _hmm_section(close)
    L += ["", DISCLAIMER]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Raport de regim de piata.")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--data-dir", help="cache daily backfilled")
    ap.add_argument("--universe", help="CSV long OHLCV (ex. data/sp500.csv)")
    ap.add_argument("--window", type=int, default=20)
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--no-backtest", action="store_true", help="sari peste walk-forward")
    ap.add_argument("--no-hmm", action="store_true", help="sari peste stratul HMM")
    args = ap.parse_args(argv)
    if not args.data_dir and not args.universe:
        raise SystemExit("Da --data-dir SAU --universe.")
    dates, close, bars = _load_close(args.symbol.upper(), args.data_dir, args.universe)
    print(regime_report(args.symbol.upper(), dates, close, bars,
                        window=args.window, threshold=args.threshold,
                        horizon=args.horizon, backtest=not args.no_backtest,
                        hmm=not args.no_hmm))


if __name__ == "__main__":
    sys.exit(main())
