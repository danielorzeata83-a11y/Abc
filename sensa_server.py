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
from sensa.finra import Finra
from sensa.hub import Hub
from sensa.providers import Cboe, Finnhub, FredApi, YAHOO_RSS, http_fetch, http_post, yahoo_news
from sensa.thirteenf import Figi, ThirteenF
from sensa.watch import Watcher
from sensa.yahoo_chart import YahooChart
from sensa.darkpool import DarkPool
from sensa.insiders import InsiderService
from sensa.investors import InvestorService, UnknownTicker
from sensa.managers import browse
from sensa.politicians import PoliticiansService
from sensa.ui import (BASE_CSS, LINK_JS, NAV_CSS, nav, render_alerts, render_dark_pool, render_filing, render_insiders, render_institutional, render_investors, render_lab, render_picks, render_stock, render_latest_filings,
                      render_manager, render_managers, render_political, render_smart_money)

DISCLAIMER = "Research artifact - not investment advice."
_SYM = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_CIK = re.compile(r"^[0-9]{1,10}$")
_ACC18 = re.compile(r"^[0-9]{18}$")
_LETTER = re.compile(r"^[a-z0]$")
_MGR_PAGE = re.compile(r"^([0-9]{1,10})(?:-[a-z0-9\-]{0,100})?$")
DEFAULT_WATCHLIST = ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "SPY", "QQQ")

_STATIC_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "markov", "intraday",
                          "static", "lightweight-charts.standalone.production.js")

_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Options Dashboard</title>
<style>
__BASECSS__
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
.symbar{display:flex;gap:.8rem;align-items:center;flex-wrap:wrap;padding:.6rem 1rem}
.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:.5rem 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:4px}
.tile{padding:.5rem;border-radius:4px;font-size:.78rem;color:#fff}.tile b{display:block;font-size:.9rem}
.wide{grid-column:1/-1}.tf{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px;padding:.2rem .6rem;margin-right:4px;cursor:pointer}
.tf.on{border-color:var(--acc);color:var(--acc)}
.err{color:var(--dn);font-size:.85rem}footer{color:var(--mut);font-size:.75rem;padding:0 1rem 1rem}
@media(max-width:480px){main{padding:.6rem;gap:.6rem}}
</style></head><body>
__NAV__<div class="symbar"><span class="mut">symbol</span> <select id="sym">__OPTIONS__</select> <a id="open" href="#">Open stock page →</a></div>
<main>
<section class="card wide"><h3>Chart</h3><div id="tfs"></div><div id="chart" style="height:340px;margin-top:.5rem"></div><div id="chartmsg"></div></section>
<section class="card"><h3>Top gainers</h3><div id="gain"></div></section>
<section class="card"><h3>Top losers</h3><div id="lose"></div></section>
<section class="card"><h3>Sector heatmap</h3><div id="sect" class="tiles"></div></section>
<section class="card"><h3>Analyst consensus</h3><div id="analyst"></div></section>
<section class="card"><h3>Options snapshot</h3><div id="opts"></div></section>
<section class="card"><h3>Treasury yield curve</h3><div id="yc"></div></section>
<section class="card"><h3>Short volume (FINRA)</h3><div id="shv"></div></section>
<section class="card"><h3>Insider trades (Form 4)</h3><div id="ins"></div></section>
<section class="card"><h3>Market news</h3><div id="news"></div></section>
</main><footer>__DISCLAIMER__ Data: Cboe delayed quotes (~15 min), FRED, Yahoo Finance RSS, SEC EDGAR, FINRA. Charts: TradingView Lightweight Charts™ (Apache-2.0).</footer>
<script src="/static/lightweight-charts.js"></script>
<script>__LINKJS__</script>
<script>
const $=id=>document.getElementById(id);
const el=(t,txt,cls)=>{const e=document.createElement(t);if(txt!=null)e.textContent=txt;if(cls)e.className=cls;return e};
const safeUrl=u=>/^https?:\\/\\//i.test(u)?u:null;
async function api(p){const r=await fetch(p);const j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function fail(box,e){box.replaceChildren(el('div',String(e.message||e),'err'))}
function rows(box,list){const t=el('table');for(const r of list){const tr=el('tr');
 const sc=el('td');sc.append(tkLink(r.symbol));tr.append(sc,el('td',r.price.toFixed(2),'mut'),
 el('td',(r.change_pct>0?'+':'')+r.change_pct+'%',r.change_pct>0?'up':'dn'));t.append(tr)}
 box.replaceChildren(list.length?t:el('span','no data','mut'))}
let chart,candleS,volS,tf='1day';
function initChart(){if(chart||!window.LightweightCharts)return;
 chart=LightweightCharts.createChart($('chart'),{autoSize:true,layout:{background:{color:'#161b22'},textColor:'#e6edf3'},
  grid:{vertLines:{color:'#21262d'},horzLines:{color:'#21262d'}},timeScale:{timeVisible:true}});
 candleS=chart.addCandlestickSeries();
 volS=chart.addHistogramSeries({priceScaleId:'',priceFormat:{type:'volume'},color:'#58a6ff55'});
 volS.priceScale().applyOptions({scaleMargins:{top:0.8,bottom:0}})}
async function bars(s){const m=$('chartmsg');m.textContent='';initChart();
 if(!chart){m.replaceChildren(el('div','chart library failed to load','err'));return}
 try{const r=await api('/api/bars/'+s+'?tf='+tf);
  candleS.setData(r.map(b=>({time:b.time,open:b.open,high:b.high,low:b.low,close:b.close})));
  volS.setData(r.map(b=>({time:b.time,value:b.volume})));chart.timeScale().fitContent()}
 catch(e){candleS.setData([]);volS.setData([]);fail(m,e)}}
for(const t of ['15m','30m','1h','4h','1day']){const b=el('button',t,'tf'+(t===tf?' on':''));
 b.onclick=()=>{tf=t;document.querySelectorAll('.tf').forEach(x=>x.classList.toggle('on',x===b));bars($('sym').value)};$('tfs').append(b)}
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
async function sectors(){const b=$('sect');try{const r=await api('/api/sectors');
 b.replaceChildren(...r.map(x=>{const d=el('div',null,'tile'),a=Math.min(Math.abs(x.change_pct)/2,1);
  d.style.background=x.change_pct>=0?`rgba(63,185,80,${0.25+a*0.6})`:`rgba(248,81,73,${0.25+a*0.6})`;
  d.append(el('b',x.symbol),el('span',x.sector),el('div',(x.change_pct>0?'+':'')+x.change_pct+'%'));return d}))}catch(e){fail(b,e)}}
async function curve(){const b=$('yc');try{const y=await api('/api/yield-curve');const p=y.points;
 const W=320,H=140,v=p.map(x=>x[1]),lo=Math.min(...v)-.1,hi=Math.max(...v)+.1;
 const pts=p.map((x,i)=>(10+i*(W-20)/(p.length-1))+','+(H-20-(x[1]-lo)/(hi-lo)*(H-40))).join(' ');
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('width','100%');
 const pl=document.createElementNS(ns,'polyline');pl.setAttribute('points',pts);
 pl.setAttribute('fill','none');pl.setAttribute('stroke','#58a6ff');pl.setAttribute('stroke-width','2');svg.append(pl);
 b.replaceChildren(svg,el('div',y.date+' · '+p[0][0]+' '+p[0][1]+'% → '+p[p.length-1][0]+' '+p[p.length-1][1]+'%','mut'))}catch(e){fail(b,e)}}
async function shortvol(s){const b=$('shv');try{const x=await api('/api/short-volume/'+s);
 if(!x){b.replaceChildren(el('span','no data for '+s,'mut'));return}
 const pct=x.short_ratio==null?'-':(x.short_ratio*100).toFixed(1)+'%',t=el('table');
 for(const [k,v] of [['Date',x.date],['Short ratio',pct],['Short vol',Math.round(x.short_volume).toLocaleString()],['Total vol',Math.round(x.total_volume).toLocaleString()]]){
  const tr=el('tr');tr.append(el('td',k,'mut'),el('td',v));t.append(tr)}
 b.replaceChildren(t,el('div','Share of daily volume that was short sales (not short interest).','mut'))}catch(e){fail(b,e)}}
async function insiders(s){const b=$('ins');try{const r=await api('/api/insiders/'+s);
 if(!r.length){b.replaceChildren(el('span','no recent open-market trades for '+s,'mut'));return}
 const t=el('table');for(const x of r){const tr=el('tr');
  tr.append(el('td',x.owner+' · '+x.role),el('td',x.side+' '+x.shares+' @ '+x.price,x.side==='buy'?'up':'dn'));t.append(tr)}
 b.replaceChildren(t)}catch(e){fail(b,e)}}
async function news(){const b=$('news');try{const n=await api('/api/news'),u=el('ul');
 for(const x of n){const li=el('li'),h=safeUrl(x.url),a=el('a',x.headline);if(h){a.href=h;a.target='_blank';a.rel='noopener noreferrer'}
  li.append(a,el('span',' '+(x.source||''),'mut'));u.append(li)}b.replaceChildren(u)}catch(e){fail(b,e)}}
const syncOpen=()=>{$('open').href='/stock/'+encodeURIComponent($('sym').value)};syncOpen();
$('sym').onchange=e=>{syncOpen();analyst(e.target.value);opts(e.target.value);insiders(e.target.value);shortvol(e.target.value);bars(e.target.value)};
movers();sectors();news();curve();analyst($('sym').value);opts($('sym').value);insiders($('sym').value);shortvol($('sym').value);bars($('sym').value);
setInterval(()=>{movers();sectors()},60000);
</script></body></html>"""


def render_index(watchlist):
    page = _PAGE.replace("__BASECSS__", BASE_CSS + NAV_CSS).replace("__NAV__", nav("dash")).replace("__LINKJS__", LINK_JS)
    opts = "".join(f'<option value="{s}">{s}</option>' for s in watchlist)
    return (page.replace("__OPTIONS__", opts)
                 .replace("__DISCLAIMER__", DISCLAIMER))


def write_quietly(wfile, data):
    """A browser that reloads or navigates away aborts its connection mid-response;
    that is normal, not an error worth a traceback."""
    try:
        wfile.write(data)
    except ConnectionError:      # aborted / reset / broken pipe
        pass


_LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
_MAX_BODY = 4096


def _make_handler(hub, watchlist, watcher=None, smart=None, insiders=None, darkpool=None, politicians=None, investors=None, live=None, perf=None, lab=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):   # quiet; never echo URLs (no key leakage)
            pass

        def _send(self, code, body, ctype):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            write_quietly(self.wfile, data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj), "application/json")

        def do_GET(self):
            u = urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            if u.path == "/":
                self._send(200, render_index(watchlist), "text/html; charset=utf-8")
                return
            if u.path == "/static/lightweight-charts.js":
                try:
                    with open(_STATIC_JS, "rb") as fh:
                        self._send(200, fh.read(), "application/javascript")
                except OSError:
                    self._send(404, "missing vendored JS", "text/plain")
                return
            if u.path.rstrip("/") == "/smart-money":
                self._send(200, render_smart_money(), "text/html; charset=utf-8")
                return
            if u.path in ("/api/smart-money/overview", "/api/smart-money/status"):
                if smart is None:
                    self._json(503, {"error": "Smart Money overview is not configured (set SEC_CONTACT)"})
                    return
                try:
                    if u.path.endswith("overview"):
                        live_view = (parse_qs(u.query).get("view") or [""])[0] == "live"
                        self._json(200, smart.live_overview() if live_view else smart.overview())
                    else:
                        self._json(200, smart.status())
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if u.path.rstrip("/") == "/smart-money/alerts":
                self._send(200, render_alerts(), "text/html; charset=utf-8")
                return
            if u.path == "/api/watch":
                if watcher is None:
                    self._json(503, {"error": "watching is not configured (set SEC_CONTACT)"})
                else:
                    self._json(200, {"following": watcher.following(), "events": watcher.events()})
                return
            if u.path.rstrip("/") == "/institutional-investor":
                self._send(200, render_institutional(), "text/html; charset=utf-8")
                return
            if len(parts) == 3 and parts[:2] == ["institutional-investor", "managers"]:
                if not _LETTER.match(parts[2].lower()):
                    self._send(404, "not found", "text/plain")
                    return
                self._send(200, render_managers(parts[2].lower()), "text/html; charset=utf-8")
                return
            if parts == ["institutional-investor", "latest-filings"]:
                self._send(200, render_latest_filings(), "text/html; charset=utf-8")
                return
            if len(parts) == 2 and parts[0] == "institutional-investor" and _ACC18.match(parts[1]):
                self._send(200, render_filing(parts[1]), "text/html; charset=utf-8")
                return
            if u.path.rstrip("/") == "/political-trades":
                self._send(200, render_political(), "text/html; charset=utf-8")
                return
            if parts[:2] == ["api", "political-trades"] and len(parts) <= 3:
                if politicians is None:
                    self._json(503, {"error": "political trades are not configured"})
                    return
                try:
                    if len(parts) == 3:
                        if parts[2] != "status":
                            self._send(404, "not found", "text/plain")
                            return
                        self._json(200, politicians.status())
                        return
                    q = parse_qs(u.query)
                    days = min(730, max(1, int((q.get("days") or ["90"])[0])))
                    limit = min(300, max(1, int((q.get("limit") or ["100"])[0])))
                    side = (q.get("side") or [""])[0]
                    ticker = (q.get("ticker") or [""])[0].upper()
                    member = (q.get("member") or [""])[0][:60]
                    if side not in ("", "buy", "sell") or (ticker and not _SYM.match(ticker)):
                        self._json(400, {"error": "bad filter"})
                        return
                    self._json(200, politicians.overview(days=days, side=side or None, ticker=ticker or None,
                                                         member=member or None, limit=limit))
                except ValueError:
                    self._json(400, {"error": "bad parameters"})
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if len(parts) == 2 and parts[0] == "stock":
                if not _SYM.match(parts[1].upper()):
                    self._send(404, "not found", "text/plain")
                else:
                    self._send(200, render_stock(parts[1].upper()), "text/html; charset=utf-8")
                return
            if len(parts) == 3 and parts[0] == "stock" and parts[2] == "investors":
                if not _SYM.match(parts[1].upper()):
                    self._send(404, "not found", "text/plain")
                else:
                    self._send(200, render_investors(parts[1].upper()), "text/html; charset=utf-8")
                return
            if u.path.rstrip("/") == "/picks":
                self._send(200, render_picks(), "text/html; charset=utf-8")
                return
            if u.path.rstrip("/") == "/portfolio-lab":
                self._send(200, render_lab(), "text/html; charset=utf-8")
                return
            if parts[:2] == ["api", "lab"]:
                if lab is None:
                    self._json(503, {"error": "the portfolio lab is not configured (set SEC_CONTACT)"})
                elif parts[2:] == ["status"]:
                    self._json(200, {"status": lab.status(), "runs": lab.runs()})
                elif len(parts) == 4 and parts[2] == "result":
                    try:
                        r = lab.result(parts[3])
                        self._json(200, {k: v for k, v in r.items() if k not in ("rebalances", "daily_returns")})
                    except KeyError:
                        self._json(404, {"error": "no such run"})
                elif len(parts) == 5 and parts[2] == "file":
                    try:
                        path = lab.file(parts[3], parts[4])
                        with open(path, "rb") as fh:
                            self._send(200, fh.read(), "text/plain; charset=utf-8" if path.endswith((".md", ".csv")) else "application/json")
                    except KeyError:
                        self._send(404, "not found", "text/plain")
                else:
                    self._send(404, "not found", "text/plain")
                return
            if len(parts) == 3 and parts[:2] == ["api", "portfolio"]:
                if perf is None:
                    self._json(503, {"error": "performance is not configured (set SEC_CONTACT)"})
                elif not _CIK.match(parts[2]):
                    self._json(400, {"error": "bad CIK"})
                else:
                    try:
                        self._json(200, perf.portfolio.fund(f"{int(parts[2]):010d}"))
                    except KeyError:
                        self._json(404, {"error": "no 13F report found for that manager"})
                    except DataUnavailable as e:
                        self._json(503, {"error": str(e)})
                return
            if len(parts) == 3 and parts[:2] == ["api", "performance"]:
                if perf is None:
                    self._json(503, {"error": "performance is not configured (set SEC_CONTACT)"})
                elif parts[2] not in perf.jobs:
                    self._send(404, "not found", "text/plain")
                else:
                    job = perf.jobs[parts[2]]
                    try:
                        r = job.result()
                        self._json(200, {"status": job.status(), "data": r["data"], "generated": r["generated"], "message": ""})
                    except DataUnavailable as e:
                        self._json(200, {"status": job.status(), "data": None, "generated": None, "message": str(e)})
                return
            if u.path == "/api/live/status":
                if live is None:
                    self._json(503, {"error": "live 13F reading is not configured (set SEC_CONTACT)"})
                else:
                    self._json(200, live.status())
                return
            if len(parts) == 3 and parts[:2] == ["api", "investors"]:
                if investors is None:
                    self._json(503, {"error": "investor data is not configured (set SEC_CONTACT)"})
                    return
                if not _SYM.match(parts[2].upper()):
                    self._json(400, {"error": "bad symbol"})
                    return
                q = parse_qs(u.query)
                one = lambda k, d: (q.get(k) or [d])[0]
                try:
                    self._json(200, investors.lookup(parts[2].upper(), page=int(one("page", "1")), limit=int(one("limit", "20")),
                                                     sort_by=one("sortBy", "value"), sort_order=one("sortOrder", "desc")))
                except ValueError as e:
                    self._json(400, {"error": str(e) if "must be" in str(e) else "bad parameters"})
                except UnknownTicker as e:
                    self._json(404, {"error": str(e)})
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if u.path.rstrip("/") == "/dark-pool":
                self._send(200, render_dark_pool(), "text/html; charset=utf-8")
                return
            if parts[:2] == ["api", "dark-pool"] and len(parts) <= 3:
                if darkpool is None:
                    self._json(503, {"error": "dark pool data is not configured"})
                    return
                try:
                    if len(parts) == 3:
                        if not _SYM.match(parts[2].upper()):
                            self._json(400, {"error": "bad symbol"})
                            return
                        self._json(200, darkpool.symbol(parts[2]))
                    else:
                        top = min(200, max(1, int((parse_qs(u.query).get("top") or ["50"])[0])))
                        self._json(200, darkpool.overview(top))
                except ValueError:
                    self._json(400, {"error": "bad parameters"})
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if u.path.rstrip("/") == "/inside-trade":
                self._send(200, render_insiders(), "text/html; charset=utf-8")
                return
            if parts[:2] == ["api", "insider-trades"] and len(parts) <= 3:
                if insiders is None:
                    self._json(503, {"error": "insider data is not configured (set SEC_CONTACT)"})
                    return
                try:
                    if len(parts) == 3 and parts[2] == "status":
                        self._json(200, insiders.status())
                    elif len(parts) == 3:
                        if not _SYM.match(parts[2].upper()):
                            self._json(400, {"error": "bad symbol"})
                            return
                        self._json(200, insiders.symbol(parts[2]))
                    else:
                        q = parse_qs(u.query)
                        days = min(365, max(1, int((q.get("days") or ["30"])[0])))
                        plans = (q.get("plans") or ["1"])[0] != "0"
                        self._json(200, insiders.overview(days, plans))
                except ValueError:
                    self._json(400, {"error": "bad parameters"})
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if u.path == "/api/managers":
                if smart is None:
                    self._json(503, {"error": "manager list is not configured (set SEC_CONTACT)"})
                    return
                q = parse_qs(u.query)
                try:
                    off, lim = int((q.get("offset") or ["0"])[0]), int((q.get("limit") or ["50"])[0])
                except ValueError:
                    self._json(400, {"error": "bad paging"})
                    return
                letter = (q.get("letter") or [""])[0].lower()
                query = (q.get("q") or [""])[0][:60]
                if not query and not _LETTER.match(letter):
                    self._json(400, {"error": "letter must be a-z or 0"})
                    return
                try:
                    self._json(200, browse(smart.managers(), letter, off, lim, query or None))
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if u.path == "/api/latest-filings":
                try:
                    lim = min(100, max(1, int((parse_qs(u.query).get("limit") or ["50"])[0])))
                    self._json(200, hub.latest_filings(lim))
                except ValueError:
                    self._json(400, {"error": "bad limit"})
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
                return
            if len(parts) == 3 and parts[:2] == ["api", "filing"]:
                if not _ACC18.match(parts[2]):
                    self._json(400, {"error": "bad accession"})
                    return
                try:
                    self._json(200, hub.filing(parts[2]))
                except DataUnavailable as e:
                    self._json(404 if "not found" in str(e) else 503, {"error": str(e)})
                return
            if len(parts) == 3 and parts[0] == "institutional-investor" and parts[1] == "manager":
                m = _MGR_PAGE.match(parts[2].lower())
                if not m:
                    self._send(404, "not found", "text/plain")
                    return
                self._send(200, render_manager(m.group(1).zfill(10)), "text/html; charset=utf-8")
                return
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "manager":
                if not _CIK.match(parts[2]):
                    self._json(400, {"error": "bad cik"})
                    return
                try:
                    if len(parts) == 3:
                        self._json(200, hub.manager(parts[2]))
                    elif len(parts) == 4 and parts[3] == "filings":
                        q = parse_qs(u.query)
                        off = max(0, int((q.get("offset") or ["0"])[0] or 0))
                        lim = min(50, max(1, int((q.get("limit") or ["20"])[0] or 20)))
                        self._json(200, hub.manager_filings(parts[2], off, lim))
                    else:
                        self._send(404, "not found", "text/plain")
                except ValueError:
                    self._json(400, {"error": "bad paging"})
                except DataUnavailable as e:
                    self._json(503, {"error": str(e)})
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
                elif route == "quote" and arg:
                    payload = hub.quote(arg)
                elif route == "company" and arg:
                    payload = hub.company(arg)
                elif route == "options" and arg:
                    payload = hub.options(arg)
                elif route == "short-volume" and arg:
                    payload = hub.short_volume(arg)
                elif route == "bars" and arg:
                    payload = hub.candles(arg, parse_qs(u.query).get("tf", ["1h"])[0])
                elif route == "sectors":
                    payload = hub.sectors()
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
            except ValueError as e:
                self._json(400, {"error": str(e)})
            except DataUnavailable as e:
                self._json(503, {"error": str(e)})

        def do_POST(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0] if not (self.headers.get("Host") or "").startswith("[") \
                else (self.headers.get("Host") or "").split("]")[0] + "]"
            if host not in _LOCAL_HOSTS:                    # DNS-rebinding guard
                self._json(403, {"error": "forbidden host"})
                return
            if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
                self._json(415, {"error": "application/json required"})   # blocks cross-site form posts
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = -1
            if n < 0 or n > _MAX_BODY:
                self._json(413, {"error": "body too large"})
                return
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError
            except ValueError:
                self._json(400, {"error": "bad json"})
                return
            route = urlparse(self.path).path
            if route == "/api/political-trades/refresh":
                if politicians is None:
                    self._json(503, {"error": "political trades are not configured"})
                else:
                    self._json(200, {"started": politicians.start(force=bool(body.get("force")))})
                return
            if route == "/api/insider-trades/refresh":
                if insiders is None:
                    self._json(503, {"error": "insider data is not configured (set SEC_CONTACT)"})
                else:
                    self._json(200, {"started": insiders.start(force=bool(body.get("force")))})
                return
            pp = [x for x in route.split("/") if x]
            if pp == ["api", "lab", "run"]:
                if lab is None:
                    self._json(503, {"error": "the portfolio lab is not configured (set SEC_CONTACT)"})
                    return
                try:
                    self._json(200, {"run_id": lab.submit(body)})
                except ValueError as e:
                    self._json(400, {"error": str(e)})
                except DataUnavailable as e:                  # a RuntimeError subclass: must be caught first
                    self._json(503, {"error": str(e)})
                except RuntimeError as e:
                    self._json(409, {"error": str(e)})
                return
            if len(pp) == 4 and pp[:2] == ["api", "performance"] and pp[3] == "refresh":
                if perf is None or pp[2] not in perf.jobs:
                    self._json(503 if perf is None else 404, {"error": "unknown performance view"})
                else:
                    self._json(200, {"started": perf.jobs[pp[2]].start(force=bool(body.get("force")))})
                return
            if route == "/api/smart-money/refresh":
                if smart is None:
                    self._json(503, {"error": "Smart Money overview is not configured (set SEC_CONTACT)"})
                else:
                    self._json(200, {"started": smart.start(force=bool(body.get("force")))})
                return
            if watcher is None:
                self._json(503, {"error": "watching is not configured (set SEC_CONTACT)"})
                return
            try:
                if route in ("/api/watch/follow", "/api/watch/unfollow"):
                    cik = str(body.get("cik", "")).strip()
                    if not _CIK.match(cik):
                        self._json(400, {"error": "bad cik"})
                        return
                    (watcher.follow if route.endswith("/follow") else watcher.unfollow)(cik)
                    self._json(200, {"following": watcher.following()})
                elif route == "/api/watch/check":
                    self._json(200, {"new_events": len(watcher.check())})
                else:
                    self._send(404, "not found", "text/plain")
            except DataUnavailable as e:
                self._json(503, {"error": str(e)})

    return Handler


def make_server(hub, host, port, watchlist, watcher=None, smart=None, insiders=None, darkpool=None, politicians=None, investors=None, live=None, perf=None, lab=None):
    return ThreadingHTTPServer((host, port), _make_handler(hub, tuple(watchlist), watcher, smart, insiders, darkpool, politicians, investors, live, perf, lab))


def build_hub():
    from markov.intraday.alphavantage import AlphaVantageDailyProvider
    from markov.intraday.service import Config
    from sensa.candles import make_candles_fn
    data_dir = Config.from_env().data_dir
    av = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    key = os.environ.get("FINNHUB_API_KEY", "").strip()

    def news(symbol):
        return yahoo_news(http_fetch(YAHOO_RSS.format(sym=symbol or "SPY")))

    fred = FredApi(os.environ.get("FRED_API_KEY", "").strip())
    sec = os.environ.get("SEC_CONTACT", "").strip()
    figi = Figi(post=lambda url, payload: http_post(url, payload))
    company_fn = None
    if sec:
        from sensa.company import CompanyInfo
        from sensa.shares_out import SharesOutstanding
        ua = {"User-Agent": f"Abc-dashboard-research/1.0 {sec}"}
        sec_get = lambda url: http_fetch(url, ua)
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "13f")
        company_fn = CompanyInfo(sec_get, SharesOutstanding(sec_get, os.path.join(cache_dir, "shares_out.json"))).get
    return Hub(Cboe(), news, fred.curve, analyst=Finnhub(key) if key else None,
               edgar=Edgar(sec, http_fetch) if sec else None, finra=Finra(http_fetch),
               candles_fn=make_candles_fn(data_dir, AlphaVantageDailyProvider(av) if av else None, secret=av,
                                          yahoo=YahooChart(http_fetch)),
               thirteenf=ThirteenF(sec, http_fetch) if sec else None, figi=figi, company_fn=company_fn,
               cache_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "13f"))


def telegram_notifier():
    """Callable(text) when TELEGRAM_TOKEN and TELEGRAM_CHAT_ID are set, else None."""
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        return None
    from markov.telegram import send_message
    return lambda text: send_message(token, chat, text)


def build_smart(contact):
    """Cross-fund Smart Money overview (top managers from SEC's quarterly bulk data sets)."""
    if not contact:
        return None
    from smart_money_build import DATA_DIR, PAGE, make_downloader
    from sensa.smart_money import OverviewService
    data_dir = os.environ.get("SMART_MONEY_DIR", "").strip() or DATA_DIR
    figi = Figi(http_post, min_interval=2.5, cache_path=os.path.join(data_dir, "figi.json"))
    ua = {"User-Agent": f"Abc-dashboard-research/1.0 {contact}"}
    return OverviewService(data_dir, lambda: http_fetch(PAGE, ua), make_downloader(contact), figi, top=100,
                           notify=telegram_notifier())


def build_investors(smart, contact):
    """Institutional holders of one stock, from the index that the Smart Money Update builds."""
    if smart is None:
        return None
    ua = {"User-Agent": f"Abc-dashboard-research/1.0 {contact}"}
    return InvestorService(smart.data_dir, smart.figi, lambda url: http_fetch(url, ua))


def build_live(smart, thirteenf):
    """Reads each new 13F report for the quarter the bulk data set does not cover yet, straight from EDGAR."""
    if smart is None or thirteenf is None:
        return None
    from sensa.holders import meta
    from sensa.live13f import LiveStore, LiveUpdater

    def bulk_period():
        return meta(os.path.join(smart.data_dir, "holders.db"))["period"]
    def size_rank():
        import sqlite3
        from sensa.holders import _uri
        con = sqlite3.connect(_uri(os.path.join(smart.data_dir, "holders.db")), uri=True)
        try:
            return {cik: i for i, (cik,) in enumerate(con.execute("SELECT cik FROM filers WHERE q = 0 ORDER BY aum DESC"))}
        finally:
            con.close()
    def rebuild_view(added):
        from sensa.live_overview import refresh_live_overview
        try:
            refresh_live_overview(smart.data_dir, smart.figi)
        except DataUnavailable:
            pass                                          # no overview yet: nothing to compare with
    return LiveUpdater(LiveStore(os.path.join(smart.data_dir, "live13f.db")), thirteenf, bulk_period, size_rank=size_rank,
                       on_update=rebuild_view)


class Perf:
    """Prices + the portfolio service and the three background leaderboards."""
    def __init__(self, portfolio, jobs):
        self.portfolio, self.jobs = portfolio, jobs


def build_perf(smart, insiders, politicians):
    if smart is None:
        return None
    from sensa.perf_service import PerfJob, PortfolioService, funds_board, insiders_board, members_board, picks_board
    from sensa.prices import PriceBook
    from sensa.universe import load_overview
    d = smart.data_dir
    yc = YahooChart(http_fetch)
    prices = PriceBook(lambda t: yc.candles(t, "1day"), cache_path=os.path.join(d, "prices.json"), retries=2, backoff=1.0)
    portfolio = PortfolioService(os.path.join(d, "holders.db"), os.path.join(d, "live13f.db"), smart.figi, prices)
    jobs = {"funds": PerfJob("pricing the top funds' portfolios", lambda: funds_board(load_overview(d), portfolio),
                             os.path.join(d, "perf_funds.json"))}
    from sensa.lab_service import AdjustedCache
    adj = AdjustedCache(lambda t, years: yc.adjusted(t, years), os.path.join(d, "lab", "adjusted_prices.json"))

    def overview():
        return load_overview(d)
    jobs["picks"] = PerfJob("building the picks", lambda: picks_board(overview, prices, insiders, politicians, adj.get), os.path.join(d, "perf_picks.json"))
    if politicians is not None:
        jobs["members"] = PerfJob("pricing House trades", lambda: members_board(politicians, prices), os.path.join(d, "perf_members.json"))
    if insiders is not None:
        jobs["insiders"] = PerfJob("pricing insider trades", lambda: insiders_board(insiders, prices), os.path.join(d, "perf_insiders.json"))
    return Perf(portfolio, jobs)


def build_lab(smart, insiders, watchlist):
    if smart is None:
        return None
    from sensa.lab_service import LabService
    from sensa.universe import load_overview
    yc = YahooChart(http_fetch)

    def overview():
        try:
            return load_overview(smart.data_dir)
        except DataUnavailable:
            return None
    return LabService(smart.data_dir, lambda t, years: yc.adjusted(t, years), overview=overview, insiders=insiders, watchlist=watchlist)


def build_insiders(contact):
    """Quarterly SEC insider data set (Form 4 open-market trades)."""
    if not contact:
        return None
    from smart_money_build import make_downloader
    data_dir = os.environ.get("INSIDERS_DIR", "").strip() or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "insiders")
    page = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
    ua = {"User-Agent": f"Abc-dashboard-research/1.0 {contact}"}
    return InsiderService(data_dir, lambda: http_fetch(page, ua), make_downloader(contact))


def build_politicians(contact):
    """US House Periodic Transaction Reports (no SEC contact needed; one is added to the User-Agent when set)."""
    from smart_money_build import make_downloader
    data_dir = os.environ.get("POLITICIANS_DIR", "").strip() or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "politicians")
    return PoliticiansService(data_dir, make_downloader(contact or "personal-research"))


def _smart_loop(smart, hours, stop):
    while True:
        smart.start()                    # at launch, then every `hours`; no-op unless SEC published a newer quarter
        if stop.wait(hours * 3600):
            break


def _perf_loop(job, ok_hours, retry_minutes, stop):
    """Run a leaderboard job, then wait: a few minutes after a failure (data not built yet), hours after a success."""
    while True:
        job.start()
        job.wait()
        failed = job.state().get("state") == "error"
        if stop.wait(retry_minutes * 60 if failed else ok_hours * 3600):
            break


def build_watcher(hub):
    """Follow-list + signals. Needs SEC_CONTACT (same as the 13F pages). Telegram is optional."""
    if hub.thirteenf is None:
        return None
    notify = telegram_notifier()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "watch", "watch.json")
    return Watcher(hub.thirteenf, hub.figi, path, notify=notify)


def _watch_loop(watcher, minutes, stop):
    while not stop.wait(minutes * 60):
        try:
            for ev in watcher.check():
                print(f"[signal] {ev['name']} {ev['quarter']}: {ev['counts']}", flush=True)
        except Exception as e:           # never let the background thread die silently
            print(f"[watch] check failed: {type(e).__name__}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--watchlist", default=",".join(DEFAULT_WATCHLIST))
    ap.add_argument("--smart-hours", type=int, default=24,
                    help="how often to look for a newer 13F quarter for the Smart Money overview (0 = off)")
    ap.add_argument("--live-hours", type=float, default=1.0,
                    help="how often to read new 13F reports for the not-yet-published quarter from EDGAR (0 = off)")
    ap.add_argument("--watch-minutes", type=int, default=60,
                    help="how often to look for new 13F filings of followed funds (0 = off)")
    a = ap.parse_args()
    wl = [s for s in a.watchlist.upper().split(",") if _SYM.match(s)]
    hub = build_hub()
    watcher = build_watcher(hub)
    smart = build_smart(os.environ.get("SEC_CONTACT", "").strip())
    if smart is not None:
        hub.accession_lookup = smart.lookup_accession
    investors = build_investors(smart, os.environ.get("SEC_CONTACT", "").strip())
    live = build_live(smart, hub.thirteenf)
    insiders = build_insiders(os.environ.get("SEC_CONTACT", "").strip())
    politicians = build_politicians(os.environ.get("SEC_CONTACT", "").strip())
    perf = build_perf(smart, insiders, politicians)
    lab = build_lab(smart, insiders, wl)
    if a.smart_hours > 0:
        import threading
        threading.Thread(target=_smart_loop, args=(politicians, a.smart_hours, threading.Event()), daemon=True).start()
    srv = make_server(hub, a.host, a.port, wl, watcher=watcher, smart=smart, insiders=insiders,
                      darkpool=DarkPool(http_post), politicians=politicians, investors=investors, live=live, perf=perf, lab=lab)
    if insiders is not None and a.smart_hours > 0:
        import threading
        threading.Thread(target=_smart_loop, args=(insiders, a.smart_hours, threading.Event()), daemon=True).start()
    if smart is not None and a.smart_hours > 0:
        import threading
        threading.Thread(target=_smart_loop, args=(smart, a.smart_hours, threading.Event()), daemon=True).start()
    if perf is not None and a.smart_hours > 0:
        import threading
        for job in perf.jobs.values():                      # prices change daily: refresh every 6 hours
            threading.Thread(target=_perf_loop, args=(job, 6, 10, threading.Event()), daemon=True).start()
    if live is not None and a.live_hours > 0:
        import threading
        threading.Thread(target=_smart_loop, args=(live, a.live_hours, threading.Event()), daemon=True).start()
    if watcher is not None and a.watch_minutes > 0:
        import threading
        threading.Thread(target=_watch_loop, args=(watcher, a.watch_minutes, threading.Event()),
                         daemon=True).start()
    print(f"http://{a.host}:{srv.server_address[1]}  ({DISCLAIMER})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
