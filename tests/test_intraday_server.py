"""Smoke tests for the stdlib intraday server (real HTTP on 127.0.0.1:0)."""

import http.client
import json
import threading

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars
from markov.intraday.cache import write_bars
from markov.intraday.service import Config
import intraday_server as srv


def _seed(dirpath, symbol="NVDA"):
    idx = pd.date_range("2025-07-03 09:30", "2025-07-03 15:45", freq="15min")
    n = len(idx)
    o = np.linspace(100.0, 105.0, n)
    write_bars(dirpath, symbol,
               Bars(idx.to_numpy(), o, o + 1, o - 1, o + 0.5, np.full(n, 10.0)))


def _run(cfg):
    server = srv.make_server(cfg)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _get(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("GET", path)
    r = c.getresponse()
    body = r.read().decode()
    ctype = r.getheader("Content-Type")
    c.close()
    return r.status, body, ctype


def test_server_routes(tmp_path):
    _seed(str(tmp_path))
    cfg = Config(watchlist=("NVDA",), host="127.0.0.1", port=0, data_dir=str(tmp_path))
    server = _run(cfg)
    port = server.server_address[1]
    try:
        s, b, _ = _get(port, "/")
        assert s == 200 and "lightweight-charts" in b and "4h" in b

        s, b, ct = _get(port, "/static/lightweight-charts.js")
        assert s == 200 and "javascript" in ct

        s, b, _ = _get(port, "/bars?symbol=NVDA&tf=1h")
        assert s == 200
        bars = json.loads(b)
        assert isinstance(bars, list) and bars and "close" in bars[0]

        s, b, _ = _get(port, "/indicators?symbol=NVDA&tf=1h")
        assert s == 200 and "hurst" in json.loads(b)

        # validation: unknown tf, bad symbol, symbol outside watchlist -> 400
        assert _get(port, "/bars?symbol=NVDA&tf=7m")[0] == 400
        assert _get(port, "/bars?symbol=ZZZ&tf=1h")[0] == 400
        assert _get(port, "/bars?symbol=AAPL&tf=1h")[0] == 400

        # uncached symbol that IS in watchlist -> 503
        cfg2_server = server  # reuse
    finally:
        server.shutdown()


def test_503_for_uncached_symbol_in_watchlist(tmp_path):
    # NVDA seeded, MSFT in watchlist but not cached -> 503
    _seed(str(tmp_path), "NVDA")
    cfg = Config(watchlist=("NVDA", "MSFT"), host="127.0.0.1", port=0,
                 data_dir=str(tmp_path))
    server = _run(cfg)
    port = server.server_address[1]
    try:
        assert _get(port, "/bars?symbol=MSFT&tf=1h")[0] == 503
    finally:
        server.shutdown()
