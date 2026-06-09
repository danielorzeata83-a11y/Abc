"""Loader pentru flat files massive.com / stil Polygon (agregate zilnice OHLCV).

Ingereaza fisierele descarcate (CSV sau CSV.gz) si le transforma in formatul
nostru lung -- `date,open,high,low,close,volume,Name` -- exact ca data/sp500.csv,
ca sa intre direct in tot pipeline-ul (dashboard, monitor, alerta, backtest).
ZERO retea, ZERO secret: tu descarci fisierele, asta doar le citeste.

Schema confirmata massive.com:
    ticker,volume,open,close,high,low,window_start,transactions
unde window_start = Unix nanosecunde. Fisierele de MINUT (multe bare/zi) sunt
agregate automat la o bara/zi (open=first, high=max, low=min, close=last,
volume=sum); fisierele de zi trec neatinse. Maparea e tolerant la alias-uri
(o/h/l/c/v, T/symbol). NU consiliere de investitii.
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


def _date_and_ts(s, colname):
    """Serie de timp -> (date 'YYYY-MM-DD', ts int64 pt ordonare intra-zi).
    window_start e DEFINIT ca nanosecunde (docs massive) -> il fortez ns; pentru
    alte coloane numerice ghicesc unitatea dupa magnitudine."""
    if pd.api.types.is_numeric_dtype(s):
        v = float(pd.to_numeric(s, errors="coerce").dropna().iloc[0])
        unit = ("ns" if str(colname).lower() == "window_start"
                else "ns" if v > 1e17 else "ms" if v > 1e12 else "s")
        dt = pd.to_datetime(s, unit=unit, utc=True).dt.tz_localize(None)
    else:
        dt = pd.to_datetime(s, errors="coerce")
    return dt.dt.strftime("%Y-%m-%d"), dt.astype("int64")


def _parse(df, default_name=None):
    """Un flat file -> randuri normalizate [_NEED] + coloana '_ts' (ordonare)."""
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
    out["date"], out["_ts"] = _date_and_ts(df[date_col], date_col)
    if "Name" not in out.columns and default_name is not None:
        out["Name"] = default_name
    missing = [c for c in _NEED if c not in out.columns]
    if missing:
        raise ValueError(f"lipsesc coloane dupa mapare: {missing}. "
                         f"Antet primit: {list(df.columns)} -- ajusteaza maparea.")
    return out[_NEED + ["_ts"]]


def parse_flat_file(df, default_name=None):
    """DataFrame brut (un flat file) -> DataFrame lung normalizat [_NEED]."""
    return _parse(df, default_name=default_name)[_NEED]


def _aggregate_daily(raw):
    """Colapseaza randuri intra-zi (minut) la o bara/zi: open=first, high=max,
    low=min, close=last, volume=sum -- ordonate dupa timestampul real."""
    raw = raw.sort_values(["Name", "_ts"])
    g = raw.groupby(["Name", "date"], sort=True).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum")).reset_index()
    return g[_NEED]


def load_flat_files(paths, symbols=None, default_name=None, daily=True):
    """Citeste si concateneaza flat files (CSV/CSV.gz) in panou lung. Implicit
    agrega la o bara/zi (corect si pt fisierele de minut). `paths`: cai sau glob."""
    files = []
    for p in (paths if isinstance(paths, (list, tuple)) else [paths]):
        files.extend(sorted(_glob.glob(p)) or [p])
    if not files:
        raise SystemExit(f"niciun fisier pentru {paths}")
    raw = pd.concat([_parse(pd.read_csv(f), default_name=default_name)
                     for f in files], ignore_index=True)
    if symbols:
        want = {s.upper() for s in symbols}
        raw = raw[raw["Name"].astype(str).str.upper().isin(want)]
    out = _aggregate_daily(raw) if daily else raw[_NEED]
    return out.sort_values(["Name", "date"]).reset_index(drop=True)
