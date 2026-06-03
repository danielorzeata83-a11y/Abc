"""Private intraday candlestick web app (stdlib http.server, zero new deps).

Serves one self-contained page using TradingView lightweight-charts (vendored
locally) plus JSON endpoints /bars and /indicators backed by the cached 15m data
(coarser timeframes derived on demand). Bind 127.0.0.1 and reach it via an SSH
tunnel:  ssh -N -L 8765:127.0.0.1:8765 user@aws-host  -> http://localhost:8765

Research / visualisation only -- NOT investment advice.

    export ALPHAVANTAGE_API_KEY=...
    python intraday_server.py --backfill-months 12 --watchlist NVDA,AAPL,MSFT
    python intraday_server.py --no-fetch        # serve only cached data, no key
"""

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from markov.data_providers import DataUnavailable
from markov.intraday.service import Config, TIMEFRAMES, get_candles, get_features

_STATIC_JS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "markov", "intraday", "static", "lightweight-charts.standalone.production.js")
DISCLAIMER = "Research artifact - not investment advice."


def render_index(cfg):
    """One self-contained HTML page: candles + volume + VWAP + features panel."""
    syms = "".join(f'<option value="{s}">{s}</option>' for s in cfg.watchlist)
    tfs = "".join(f'<button class="tf" data-tf="{tf}">{tf}</button>' for tf in TIMEFRAMES)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Intraday -- {cfg.watchlist[0]}</title>
<style>body{{font-family:system-ui;margin:1rem;background:#0e1116;color:#e6edf3}}
#chart{{height:460px}} button.tf{{margin:2px;padding:4px 8px;cursor:pointer}}
#features{{font-size:.85rem;display:flex;flex-wrap:wrap;gap:.4rem 1.2rem;margin-top:.6rem}}
.k{{color:#8b949e}} footer{{color:#8b949e;font-size:.75rem;margin-top:1rem}}</style>
</head><body>
<h2>Intraday candlestick -- privat</h2>
<div>Simbol <select id="sym">{syms}</select> &nbsp; {tfs}</div>
<div id="chart"></div>
<div id="features"></div>
<footer>4h = ancorat la 09:30 ET (al 2-lea bucket scurt). {DISCLAIMER}</footer>
<script src="/static/lightweight-charts.js"></script>
<script>
const chart = LightweightCharts.createChart(document.getElementById('chart'),
  {{layout:{{background:{{color:'#0e1116'}},textColor:'#e6edf3'}},
    grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}}}});
const candle = chart.addCandlestickSeries();
const volume = chart.addHistogramSeries(
  {{priceScaleId:'',priceFormat:{{type:'volume'}},scaleMargins:{{top:0.8,bottom:0}}}});
const vwap = chart.addLineSeries({{color:'#d29922',lineWidth:1}});
let sym=document.getElementById('sym').value, tf='1h';
async function load(){{
  const r = await fetch(`/bars?symbol=${{sym}}&tf=${{tf}}`);
  if(!r.ok){{document.getElementById('features').textContent='(fara date)';return;}}
  const bars = await r.json();
  candle.setData(bars.map(b=>({{time:b.time,open:b.open,high:b.high,low:b.low,close:b.close}})));
  volume.setData(bars.map(b=>({{time:b.time,value:b.volume}})));
  vwap.setData(bars.filter(b=>'vwap' in b).map(b=>({{time:b.time,value:b.vwap}})));
  const f = await (await fetch(`/indicators?symbol=${{sym}}&tf=${{tf}}`)).json();
  document.getElementById('features').innerHTML = Object.entries(f).map(
    ([k,v])=>`<span><span class="k">${{k}}</span> ${{v==null?'-':(+v).toFixed(4)}}</span>`).join('');
}}
document.getElementById('sym').onchange=e=>{{sym=e.target.value;load();}};
document.querySelectorAll('button.tf').forEach(b=>b.onclick=()=>{{tf=b.dataset.tf;load();}});
load();
</script></body></html>"""


def _make_handler(cfg):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):   # quiet; never echo URLs (no key leakage)
            pass

        def _send(self, code, body, ctype):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj), "application/json")

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/":
                self._send(200, render_index(cfg), "text/html; charset=utf-8")
                return
            if u.path == "/static/lightweight-charts.js":
                try:
                    with open(_STATIC_JS, "rb") as fh:
                        self._send(200, fh.read(), "application/javascript")
                except OSError:
                    self._send(404, "missing vendored JS", "text/plain")
                return
            if u.path in ("/bars", "/indicators"):
                symbol = (q.get("symbol", [""])[0] or "").upper()
                tf = q.get("tf", [""])[0]
                if symbol not in cfg.watchlist or tf not in TIMEFRAMES:
                    self._json(400, {"error": "bad symbol or tf"})
                    return
                try:
                    payload = (get_candles(symbol, tf, cfg.data_dir)
                               if u.path == "/bars"
                               else get_features(symbol, tf, cfg.data_dir))
                    self._json(200, payload)
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            self._send(404, "not found", "text/plain")

    return Handler


def make_server(cfg):
    return ThreadingHTTPServer((cfg.host, cfg.port), _make_handler(cfg))


def _refresh_loop(cfg, stop):
    """Best-effort background refresh: one-time backfill of missing months, then
    periodic current-month refresh. Respects the free tier (<=5/min, gated by
    refresh_interval_min). Silent no-op if no API key."""
    import pandas as pd
    from markov.intraday.alphavantage import get_intraday_provider
    from markov.intraday.cache import (read_bars, write_bars, merge_bars,
                                       needs_refresh, backfill_months)

    key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        return
    prov = get_intraday_provider(f"av:{key}")

    def _store(sym, fresh):
        old = read_bars(cfg.data_dir, sym)
        write_bars(cfg.data_dir, sym, merge_bars(old, fresh) if old else fresh)

    for sym in cfg.watchlist:                      # one-time backfill
        if read_bars(cfg.data_dir, sym) is not None:
            continue
        for month in backfill_months(pd.Timestamp.utcnow(), cfg.backfill_months):
            try:
                _store(sym, prov.fetch_month(sym, month))
            except DataUnavailable:
                break                              # throttled/offline -> resume next run
            if stop.wait(13):                      # <=5/min
                return

    while not stop.is_set():                        # stay current
        for sym in cfg.watchlist:
            if needs_refresh(cfg.data_dir, sym, pd.Timestamp.utcnow(),
                             cfg.refresh_interval_min):
                try:
                    month = pd.Timestamp.utcnow().strftime("%Y-%m")
                    _store(sym, prov.fetch_month(sym, month))
                except DataUnavailable:
                    pass
                if stop.wait(13):
                    return
        stop.wait(cfg.refresh_interval_min * 60)


def main():
    ap = argparse.ArgumentParser(description="Private intraday candlestick web app.")
    ap.add_argument("--host")
    ap.add_argument("--port", type=int)
    ap.add_argument("--watchlist", help="comma-separated symbols")
    ap.add_argument("--data-dir")
    ap.add_argument("--refresh-min", type=int)
    ap.add_argument("--backfill-months", type=int)
    ap.add_argument("--no-fetch", action="store_true",
                    help="serve only cached data; no network, no API key needed")
    args = ap.parse_args()

    cfg = Config.from_env()
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port
    if args.watchlist:
        cfg.watchlist = tuple(s.strip().upper() for s in args.watchlist.split(",") if s.strip())
    if args.data_dir:
        cfg.data_dir = args.data_dir
    if args.refresh_min:
        cfg.refresh_interval_min = args.refresh_min
    if args.backfill_months:
        cfg.backfill_months = args.backfill_months

    server = make_server(cfg)
    stop = threading.Event()
    if not args.no_fetch:
        threading.Thread(target=_refresh_loop, args=(cfg, stop), daemon=True).start()
    print(f"Serving on http://{cfg.host}:{cfg.port} (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.shutdown()


if __name__ == "__main__":
    main()
