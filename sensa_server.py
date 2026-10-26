"""Own options-dashboard clone (stdlib http.server, zero new deps).

Free data: Cboe delayed quotes (prices + full option chain with greeks -> C/P
ratio and GEX), Yahoo Finance RSS (news), FRED API (yield curve, free key in
FRED_API_KEY). Optional FINNHUB_API_KEY adds analyst consensus. Bind 127.0.0.1; reach
remotely via an SSH tunnel.

    python sensa_server.py --watchlist AAPL,MSFT,NVDA,TSLA,AMZN,META,SPY,QQQ

Research / visualisation only -- NOT investment advice.
"""

import argparse
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from markov.data_providers import DataUnavailable
from sensa.edgar import Edgar
from sensa.hub import Hub
from sensa.providers import Cboe, Finnhub, FredApi, YAHOO_RSS, http_fetch, yahoo_news

DISCLAIMER = "Research artifact - not investment advice."
_SYM = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
DEFAULT_WATCHLIST = ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "SPY", "QQQ")

_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Options Dashboard</title>
<style>
:root{--bg:#0e1116;--card:#161b22;--line:#21262d;--fg:#e6edf3;--mut:#8b949e;--up:#3fb950;--dn:#f85149;--acc:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px system-ui}
header{display:flex;gap:1rem;align-items:center;padding:.8rem 1rem;border-bottom:1px solid var(--line)}
header b{font-size:1.05rem}header span{color:var(--mut)}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem;padding:1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.9rem;min-width:0}
.card h3{margin:0 0 .6rem;font-size:.8rem;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse}td{padding:.25rem 0;border-bottom:1px solid var(--line)}
td:last-child{text-align:right}.up{color:var(--up)}.dn{color:var(--dn)}.mut{color:var(--mut)}
select{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px;padding:.2rem}
a{color:var(--acc);text-decoration:none}li{margin:.35rem 0}ul{padding-left:1rem;margin:0}
.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:.5rem 0}
.err{color:var(--dn);font-size:.85rem}footer{color:var(--mut);font-size:.75rem;padding:0 1rem 1rem}
@media(max-width:480px){main{padding:.6rem;gap:.6rem}}
</style></head><body>
<header><b>Options Dashboard</b><span>symbol</span>
<select id="sym">__OPTIONS__</select></header>
<main>
<section class="card"><h3>Top gainers</h3><div id="gain"></div></section>
<section class="card"><h3>Top losers</h3><div id="lose"></div></section>
<section class="card"><h3>Analyst consensus</h3><div id="analyst"></div></section>
<section class="card"><h3>Options snapshot</h3><div id="opts"></div></section>
<section class="card"><h3>Treasury yield curve</h3><div id="yc"></div></section>
<section class="card"><h3>Insider trades (Form 4)</h3><div id="ins"></div></section>
<section class="card"><h3>Market news</h3><div id="news"></div></section>
</main><footer>__DISCLAIMER__ Data: Cboe delayed quotes (~15 min), FRED, Yahoo Finance RSS.</footer>
<script>
const $=id=>document.getElementById(id);
const el=(t,txt,cls)=>{const e=document.createElement(t);if(txt!=null)e.textContent=txt;if(cls)e.className=cls;return e};
const safeUrl=u=>/^https?:\\/\\//i.test(u)?u:null;
async function api(p){const r=await fetch(p);const j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function fail(box,e){box.replaceChildren(el('div',String(e.message||e),'err'))}
function rows(box,list){const t=el('table');for(const r of list){const tr=el('tr');
 tr.append(el('td',r.symbol),el('td',r.price.toFixed(2),'mut'),
 el('td',(r.change_pct>0?'+':'')+r.change_pct+'%',r.change_pct>0?'up':'dn'));t.append(tr)}
 box.replaceChildren(list.length?t:el('span','no data','mut'))}
async function movers(){try{const m=await api('/api/movers');rows($('gain'),m.gainers);rows($('lose'),m.losers)}catch(e){fail($('gain'),e);fail($('lose'),e)}}
async function analyst(s){const b=$('analyst');try{const a=await api('/api/analyst/'+s);
 if(!a){b.textContent='n/a (set FINNHUB_API_KEY to enable)';return}
 const tot=a.buy+a.hold+a.sell||1,bar=el('div',null,'bar');
 for(const [n,c] of [[a.buy,'var(--up)'],[a.hold,'var(--mut)'],[a.sell,'var(--dn)']]){const d=el('div');d.style.cssText='width:'+n/tot*100+'%;background:'+c;bar.append(d)}
 b.replaceChildren(el('div',a.verdict,a.verdict==='Buy'?'up':a.verdict==='Sell'?'dn':'mut'),bar,
  el('div','Buy '+a.buy+' · Hold '+a.hold+' · Sell '+a.sell+' ('+a.period+')','mut'))}catch(e){fail(b,e)}}
async function opts(s){const b=$('opts');try{const o=await api('/api/options/'+s);
 if(!o){b.textContent='no options';return}
 const c=o.cp,t=el('table');
 const m=x=>(x/1e6).toFixed(1)+'M';
 for(const [k,v] of [['Expiration',o.expiration+(o.zero_dte?' (0DTE)':'')],['Spot',o.spot],
  ['Net GEX /1%',m(o.gex.net_gex)],['Call GEX',m(o.gex.call_gex)],['Put GEX',m(o.gex.put_gex)],
  ['Call vol',c.call_volume],['Put vol',c.put_volume],
  ['C/P volume',c.volume_ratio==null?'-':c.volume_ratio],['C/P open int.',c.oi_ratio==null?'-':c.oi_ratio],['Contracts',o.chain.length]]){
  const tr=el('tr');tr.append(el('td',k,'mut'),el('td',v));t.append(tr)}
 b.replaceChildren(t)}catch(e){fail(b,e)}}
async function curve(){const b=$('yc');try{const y=await api('/api/yield-curve');const p=y.points;
 const W=320,H=140,v=p.map(x=>x[1]),lo=Math.min(...v)-.1,hi=Math.max(...v)+.1;
 const pts=p.map((x,i)=>(10+i*(W-20)/(p.length-1))+','+(H-20-(x[1]-lo)/(hi-lo)*(H-40))).join(' ');
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('width','100%');
 const pl=document.createElementNS(ns,'polyline');pl.setAttribute('points',pts);
 pl.setAttribute('fill','none');pl.setAttribute('stroke','#58a6ff');pl.setAttribute('stroke-width','2');svg.append(pl);
 b.replaceChildren(svg,el('div',y.date+' · '+p[0][0]+' '+p[0][1]+'% → '+p[p.length-1][0]+' '+p[p.length-1][1]+'%','mut'))}catch(e){fail(b,e)}}
async function insiders(s){const b=$('ins');try{const r=await api('/api/insiders/'+s);
 if(!r.length){b.replaceChildren(el('span','no recent open-market trades for '+s,'mut'));return}
 const t=el('table');for(const x of r){const tr=el('tr');
  tr.append(el('td',x.owner+' · '+x.role),el('td',x.side+' '+x.shares+' @ '+x.price,x.side==='buy'?'up':'dn'));t.append(tr)}
 b.replaceChildren(t)}catch(e){fail(b,e)}}
async function news(){const b=$('news');try{const n=await api('/api/news'),u=el('ul');
 for(const x of n){const li=el('li'),h=safeUrl(x.url),a=el('a',x.headline);if(h){a.href=h;a.target='_blank';a.rel='noopener noreferrer'}
  li.append(a,el('span',' '+(x.source||''),'mut'));u.append(li)}b.replaceChildren(u)}catch(e){fail(b,e)}}
$('sym').onchange=e=>{analyst(e.target.value);opts(e.target.value);insiders(e.target.value)};
movers();news();curve();analyst($('sym').value);opts($('sym').value);insiders($('sym').value);
setInterval(movers,60000);
</script></body></html>"""


def render_index(watchlist):
    opts = "".join(f'<option value="{s}">{s}</option>' for s in watchlist)
    return (_PAGE.replace("__OPTIONS__", opts)
                 .replace("__DISCLAIMER__", DISCLAIMER))


def _make_handler(hub, watchlist):
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
            parts = [p for p in u.path.split("/") if p]
            if u.path == "/":
                self._send(200, render_index(watchlist), "text/html; charset=utf-8")
                return
            if len(parts) < 2 or parts[0] != "api":
                self._send(404, "not found", "text/plain")
                return
            route, arg = parts[1], (parts[2].upper() if len(parts) > 2 else None)
            if arg is not None and not _SYM.match(arg):
                self._json(400, {"error": "bad symbol"})
                return
            try:
                if route == "movers":
                    syms = parse_qs(u.query).get("symbols", [""])[0]
                    syms = [s for s in syms.upper().split(",") if _SYM.match(s)] or list(watchlist)
                    payload = hub.movers(syms)
                elif route == "analyst" and arg:
                    payload = hub.analyst(arg)
                elif route == "options" and arg:
                    payload = hub.options(arg)
                elif route == "insiders":
                    payload = hub.insiders(arg)
                elif route == "news":
                    payload = hub.news(arg)
                elif route == "yield-curve":
                    payload = hub.yield_curve()
                else:
                    self._send(404, "not found", "text/plain")
                    return
                self._json(200, payload)
            except DataUnavailable as e:
                self._json(503, {"error": str(e)})

    return Handler


def make_server(hub, host, port, watchlist):
    return ThreadingHTTPServer((host, port), _make_handler(hub, tuple(watchlist)))


def build_hub():
    key = os.environ.get("FINNHUB_API_KEY", "").strip()

    def news(symbol):
        return yahoo_news(http_fetch(YAHOO_RSS.format(sym=symbol or "SPY")))

    fred = FredApi(os.environ.get("FRED_API_KEY", "").strip())
    sec = os.environ.get("SEC_CONTACT", "").strip()
    return Hub(Cboe(), news, fred.curve, analyst=Finnhub(key) if key else None,
               edgar=Edgar(sec, http_fetch) if sec else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--watchlist", default=",".join(DEFAULT_WATCHLIST))
    a = ap.parse_args()
    wl = [s for s in a.watchlist.upper().split(",") if _SYM.match(s)]
    srv = make_server(build_hub(), a.host, a.port, wl)
    print(f"http://{a.host}:{srv.server_address[1]}  ({DISCLAIMER})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
