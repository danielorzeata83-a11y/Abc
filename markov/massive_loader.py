"""Loader pentru flat files massive.com / stil Polygon (agregate zilnice OHLCV).

Ingereaza fisierele descarcate (CSV sau CSV.gz) si le transforma in formatul
nostru lung -- `date,open,high,low,close,volume,Name` -- exact ca data/sp500.csv,
ca sa intre direct in tot pipeline-ul (dashboard, monitor, alerta, backtest).
ZERO retea, ZERO secret: tu descarci fisierele, asta doar le citeste.

Schema standard asteptata:
    ticker,volume,open,close,high,low,window_start,transactions
unde window_start = epoch in nanosecunde. Maparea e tolerant la alias-uri uzuale
(o/h/l/c/v, T/symbol, t/timestamp/date). NU consiliere de investitii.
"""

import glob as _glob

import numpy as np
import pandas as pd

# OHLCV: alias lowercase -> coloana-noastra. Tickerul si data sunt tratate separat
# fiindca schema scurta Polygon foloseste 'T' (ticker) vs 't' (timestamp) -- un
# lowercase naiv le-ar confunda.
_OHLCV = {"open": "open", "o": "open", "high": "high", "h": "high",
          "low": "low", "l": "low", "close": "close", "c": "close",
          "volume": "volume", "v": "volume"}
_DATE_COLS = ("window_start", "timestamp", "date", "time")   # plus 't' exact
_NEED = ["date", "open", "high", "low", "close", "volume", "Name"]


def _normalize_date(s):
    """Serie de timp -> date 'YYYY-MM-DD'. Detecteaza epoch ns/ms/s dupa magnitudine."""
    if pd.api.types.is_numeric_dtype(s):
        v = float(pd.to_numeric(s, errors="coerce").dropna().iloc[0])
        unit = "ns" if v > 1e17 else "ms" if v > 1e12 else "s"
        dt = pd.to_datetime(s, unit=unit, utc=True).dt.tz_localize(None)
    else:
        dt = pd.to_datetime(s, errors="coerce")
    return dt.dt.strftime("%Y-%m-%d")


def parse_flat_file(df, default_name=None):
    """DataFrame brut (un flat file) -> DataFrame lung normalizat [_NEED]."""
    cols = list(df.columns)
    ren = {}
    # 1. ticker: 'T' exact (Polygon) sau ticker/symbol/name (case-insensitive)
    tcol = next((c for c in cols if str(c) == "T"
                 or str(c).lower() in ("ticker", "symbol", "name")), None)
    if tcol is not None:
        ren[tcol] = "Name"
    # 2. OHLCV dupa alias lowercase (sarim coloana de ticker)
    for c in cols:
        if c != tcol and str(c).lower() in _OHLCV:
            ren[c] = _OHLCV[str(c).lower()]
    # 3. data: din coloanele ramase (nu ticker, nu OHLCV); 't' doar exact lowercase
    date_col = next((c for c in cols if c not in ren
                     and (str(c).lower() in _DATE_COLS or str(c) == "t")), None)
    if date_col is None:
        raise ValueError(f"nu gasesc coloana de timp ({_DATE_COLS} sau 't'). "
                         f"Antet primit: {cols}")
    out = df.rename(columns=ren).copy()
    out["date"] = _normalize_date(df[date_col])
    if "Name" not in out.columns and default_name is not None:
        out["Name"] = default_name
    missing = [c for c in _NEED if c not in out.columns]
    if missing:
        raise ValueError(f"lipsesc coloane dupa mapare: {missing}. "
                         f"Antet primit: {list(df.columns)} -- ajusteaza _ALIASES.")
    return out[_NEED]


def load_flat_files(paths, symbols=None, default_name=None):
    """Citeste si concateneaza mai multe flat files (CSV/CSV.gz) in panou lung.
    `paths`: lista de cai sau pattern-uri glob. `symbols`: filtru optional."""
    files = []
    for p in (paths if isinstance(paths, (list, tuple)) else [paths]):
        files.extend(sorted(_glob.glob(p)) or [p])
    if not files:
        raise SystemExit(f"niciun fisier pentru {paths}")
    frames = [parse_flat_file(pd.read_csv(f), default_name=default_name)
              for f in files]
    out = pd.concat(frames, ignore_index=True)
    if symbols:
        want = {s.upper() for s in symbols}
        out = out[out["Name"].astype(str).str.upper().isin(want)]
    return out.sort_values(["Name", "date"]).reset_index(drop=True)
