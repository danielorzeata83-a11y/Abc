"""Trading view HTML self-contained (echivalent TradingView, offline, zero deps
externe). Date incorporate ca JSON + canvas vanilla JS: lumanari OHLC + volum +
MA50 + markeri BUY/SELL (crossover MA50) + sub-panou z realized_var, plus un
strip lead-lag (cine conduce). Zoom (rotita) si pan (drag) pe axa timpului.
Alimentat din cache + motor. NU consiliere de investitii.
"""

import json

import numpy as np
import pandas as pd

from markov.intraday.bars import Bars, resample
from markov.intraday.cache import read_bars
from markov.validation import tier1
from markov.validation.crossasset import lead_lag_matrix
from markov.validation.ensemble import zscore_causal

DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare."
_MA_W = 50


def _nan_to_none(a):
    return [None if not np.isfinite(x) else round(float(x), 4) for x in a]


def _ma(close, w=_MA_W):
    return pd.Series(np.asarray(close, dtype=float)).rolling(w, min_periods=w).mean().to_numpy()


def _crossover_signals(close, ma):
    """Markeri BUY/SELL la traversarea MA50 (semnal TIME-SERIES slab -- doar overlay
    de vizualizare, vezi results/REPORT.md). BUY = pretul trece peste MA, SELL = sub."""
    close = np.asarray(close, dtype=float)
    sig, prev = [], None
    for i in range(len(close)):
        m = ma[i]
        if not np.isfinite(close[i]) or not np.isfinite(m):
            continue
        side = close[i] >= m
        if prev is not None and side != prev:
            sig.append({"i": i, "type": "BUY" if side else "SELL"})
        prev = side
    return sig


def panel_for_symbol(symbol, bars):
    """Bars -> dict serializabil: OHLCV + MA50 + markeri + seria z realized_var."""
    df = bars.to_frame()
    close = np.asarray(df["close"], dtype=float)
    ma = _ma(close)
    volz = zscore_causal(np.asarray(tier1.INDICATORS["realized_var"](bars), dtype=float))
    return {
        "symbol": symbol,
        "dates": [str(np.datetime_as_string(t, unit="D")) for t in bars.timestamps],
        "o": _nan_to_none(df["open"]), "h": _nan_to_none(df["high"]),
        "l": _nan_to_none(df["low"]), "c": _nan_to_none(close),
        "v": _nan_to_none(df["volume"]),
        "ma": _nan_to_none(ma),
        "signals": _crossover_signals(close, ma),
        "volz": _nan_to_none(volz),
    }


def collect_panels(symbols, data_dir, horizon_tf="1day", max_bars=750):
    """Citeste cache-ul DAILY (date reale backfilled) -> lista de panouri (ultimele
    max_bars bare). Sare simbolurile lipsa din cache."""
    panels = []
    for s in symbols:
        b = read_bars(data_dir, s)
        if b is None:
            continue
        b = resample(b, horizon_tf) if horizon_tf != "15m" else b
        if max_bars and len(b) > max_bars:
            b = b.__class__(b.timestamps[-max_bars:], b.open[-max_bars:],
                            b.high[-max_bars:], b.low[-max_bars:],
                            b.close[-max_bars:], b.volume[-max_bars:])
        panels.append(panel_for_symbol(s, b))
    return panels


def panels_from_long_csv(csv_path, symbols=None, max_bars=750):
    """Construieste panouri din OHLCV REAL dintr-un CSV long (date, open, high, low,
    close, volume, Name) -- ex. data/sp500.csv. symbols=None -> toate numele."""
    raw = pd.read_csv(csv_path)
    names = symbols or sorted(raw["Name"].astype(str).unique())
    panels = []
    for s in names:
        g = raw[raw["Name"].astype(str) == str(s)].sort_values("date")
        if g.empty:
            continue
        if max_bars and len(g) > max_bars:
            g = g.iloc[-max_bars:]
        ts = pd.to_datetime(g["date"]).to_numpy()
        bars = Bars(ts, g["open"].to_numpy(dtype=float), g["high"].to_numpy(dtype=float),
                    g["low"].to_numpy(dtype=float), g["close"].to_numpy(dtype=float),
                    g["volume"].to_numpy(dtype=float))
        panels.append(panel_for_symbol(str(s), bars))
    return panels


def lead_lag_from_panels(panels):
    """[{symbol, net}] din seriile de close ale panourilor (aliniate pe datele comune).
    Agnostic de sursa (cache sau CSV). [] daca <2 simboluri sau prea putine date comune."""
    if len(panels) < 2:
        return []
    closes = {}
    for p in panels:
        c = pd.Series([np.nan if x is None else x for x in p["c"]],
                      index=pd.DatetimeIndex(p["dates"]))
        closes[p["symbol"]] = c
    rets = pd.DataFrame(closes).sort_index().pct_change().dropna(how="any")
    if len(rets) < 30:
        return []
    try:
        syms, _M, net = lead_lag_matrix(rets)
    except Exception:
        return []
    order = np.argsort(net)[::-1]
    return [{"symbol": syms[i], "net": round(float(net[i]), 4)} for i in order]


def build_html(panels, asof, leadlag=None, title="Abc — trading view"):
    """Pagina HTML self-contained (date incorporate, fara cereri externe). Cu disclaimer."""
    data_json = json.dumps({"asof": asof, "panels": panels, "leadlag": leadlag or []},
                           separators=(",", ":"))
    return (_TEMPLATE.replace("__TITLE__", title)
            .replace("__DISCLAIMER__", DISCLAIMER).replace("__DATA__", data_json))


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{--bg:#0e1117;--pane:#161b22;--grid:#222b36;--txt:#c9d1d9;--mut:#8b949e;
        --up:#26a69a;--down:#ef5350;--acc:#e3b341;--ma:#58a6ff}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
       font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif}
  header{display:flex;align-items:center;gap:14px;padding:10px 16px;
         border-bottom:1px solid var(--grid);flex-wrap:wrap}
  header h1{font-size:15px;margin:0;font-weight:600}
  #tabs{display:flex;gap:6px;flex-wrap:wrap}
  .tab{padding:4px 12px;background:var(--pane);border:1px solid var(--grid);
       border-radius:5px;cursor:pointer;color:var(--mut)}
  .tab.on{color:var(--txt);border-color:var(--acc)}
  #ll{display:flex;gap:6px;align-items:center;padding:6px 16px;flex-wrap:wrap;
      border-bottom:1px solid var(--grid);font-size:12px}
  #ll .t{color:var(--mut);margin-right:4px}
  .llp{display:flex;align-items:center;gap:5px;padding:2px 8px;border-radius:9px;
       background:var(--pane);cursor:pointer;border:1px solid transparent}
  .llp.on{border-color:var(--acc)} .llp b{font-variant-numeric:tabular-nums}
  #legend{padding:6px 16px;color:var(--mut);font-variant-numeric:tabular-nums;
          white-space:nowrap;overflow:auto}
  #legend b{color:var(--txt)} .up{color:var(--up)} .down{color:var(--down)}
  .maC{color:var(--ma)}
  #wrap{padding:0 8px} canvas{width:100%;display:block;cursor:crosshair}
  #hint{padding:4px 16px;color:var(--mut);font-size:11px}
  footer{padding:10px 16px;color:var(--mut);border-top:1px solid var(--grid);font-size:12px}
  .pill{padding:1px 7px;border-radius:9px;font-size:11px}
  .hot{background:rgba(239,83,80,.18);color:var(--down)}
  .cold{background:rgba(38,166,154,.18);color:var(--up)}
</style></head><body>
<header><h1>__TITLE__</h1><div id="tabs"></div><span id="asof" style="color:var(--mut)"></span></header>
<div id="ll"></div>
<div id="legend"></div>
<div id="wrap"><canvas id="cv"></canvas></div>
<div id="hint">rotita = zoom · drag = pan · dublu-click = reset · ▲ BUY / ▼ SELL la crossover MA50</div>
<footer>MA50 (albastru) + markeri crossover (semnal time-series slab, doar vizualizare).
Sub-panou <b>z realized_var</b> — semnalul de volatilitate al motorului (±1; rosu = risc
forward mai mare). Strip-ul lead-lag: cine conduce (transfer entropy net). __DISCLAIMER__</footer>
<script>
const DATA = __DATA__;
document.getElementById('asof').textContent = 'pana la ' + DATA.asof;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
let cur=0, hover=null, view=null, drag=null, DPR=window.devicePixelRatio||1;
const PRICE_H=380, VOL_H=70, SIG_H=110, PAD_L=8, PAD_R=64, GAP=8;
const TOTAL_H=PRICE_H+VOL_H+SIG_H+2*GAP;

function tabs(){const t=document.getElementById('tabs');t.innerHTML='';
  DATA.panels.forEach((p,i)=>{const d=document.createElement('div');
    d.className='tab'+(i===cur?' on':'');d.textContent=p.symbol;
    d.onclick=()=>select(i);t.appendChild(d)})}

function leadlag(){const el=document.getElementById('ll');
  if(!DATA.leadlag.length){el.style.display='none';return;}
  const sym=DATA.panels[cur].symbol;let h='<span class="t">LEAD-LAG</span>';
  DATA.leadlag.forEach(r=>{const lead=r.net>0;
    h+=`<span class="llp ${r.symbol===sym?'on':''}" data-s="${r.symbol}">
      <span class="${lead?'up':'down'}">${lead?'▲':'▼'}</span>${r.symbol}
      <b class="${lead?'up':'down'}">${r.net>=0?'+':''}${r.net.toFixed(4)}</b></span>`});
  el.innerHTML=h;el.querySelectorAll('.llp').forEach(e=>e.onclick=()=>{
    const i=DATA.panels.findIndex(p=>p.symbol===e.dataset.s);if(i>=0)select(i)})}

function select(i){cur=i;hover=null;const n=DATA.panels[i].c.length;
  view={s:Math.max(0,n-250),e:n};tabs();leadlag();draw()}

function dims(){const w=cv.clientWidth;cv.width=w*DPR;cv.height=TOTAL_H*DPR;
  cv.style.height=TOTAL_H+'px';ctx.setTransform(DPR,0,0,DPR,0,0);return w}

function draw(){const w=dims();const p=DATA.panels[cur];const n=p.c.length;
  const s=view.s,e=view.e,m=e-s;const L=PAD_L,R=w-PAD_R;
  const bw=Math.max(1,(R-L)/m*0.7);
  const X=i=>L+(R-L)*(i-s+0.5)/m;
  ctx.clearRect(0,0,w,TOTAL_H);
  // ---- price pane ----
  let hi=-1e18,lo=1e18;for(let i=Math.floor(s);i<e&&i<n;i++){
    if(p.h[i]!=null)hi=Math.max(hi,p.h[i]);if(p.l[i]!=null)lo=Math.min(lo,p.l[i])}
  const sp=(hi-lo)||1;hi+=sp*0.04;lo-=sp*0.04;
  const Yp=v=>16+(PRICE_H-24)*(1-(v-lo)/(hi-lo));
  grid(L,R,hi,lo,Yp,v=>v.toFixed(2));
  for(let i=Math.floor(s);i<e&&i<n;i++){if(p.c[i]==null)continue;const up=p.c[i]>=p.o[i];
    ctx.strokeStyle=ctx.fillStyle=up?'#26a69a':'#ef5350';
    ctx.beginPath();ctx.moveTo(X(i),Yp(p.h[i]));ctx.lineTo(X(i),Yp(p.l[i]));ctx.stroke();
    const y1=Yp(p.o[i]),y2=Yp(p.c[i]);
    ctx.fillRect(X(i)-bw/2,Math.min(y1,y2),bw,Math.max(1,Math.abs(y2-y1)))}
  // MA50 line
  ctx.strokeStyle='#58a6ff';ctx.lineWidth=1.3;ctx.beginPath();let st=false;
  for(let i=Math.floor(s);i<e&&i<n;i++){if(p.ma[i]==null){st=false;continue;}
    const x=X(i),y=Yp(p.ma[i]);if(!st){ctx.moveTo(x,y);st=true}else ctx.lineTo(x,y)}
  ctx.stroke();ctx.lineWidth=1;
  // BUY/SELL markers
  p.signals.forEach(g=>{if(g.i<s||g.i>=e)return;const x=X(g.i);
    if(g.type==='BUY'){const y=Yp(p.l[g.i])+10;ctx.fillStyle='#26a69a';
      tri(x,y,5,true)}else{const y=Yp(p.h[g.i])-10;ctx.fillStyle='#ef5350';tri(x,y,5,false)}});
  // ---- volume pane ----
  const vt=16+PRICE_H+GAP;let vmax=0;for(let i=Math.floor(s);i<e&&i<n;i++)
    if(p.v[i]!=null)vmax=Math.max(vmax,p.v[i]);
  for(let i=Math.floor(s);i<e&&i<n;i++){if(p.v[i]==null)continue;const up=p.c[i]>=p.o[i];
    ctx.fillStyle=up?'rgba(38,166,154,.5)':'rgba(239,83,80,.5)';
    const h=(VOL_H-6)*(p.v[i]/(vmax||1));ctx.fillRect(X(i)-bw/2,vt+VOL_H-h,bw,h)}
  label(L,vt+11,'Volum');
  // ---- signal pane (z realized_var) ----
  const gt=vt+VOL_H+GAP;const zb=gt+SIG_H;const zhi=3,zlo=-3;
  const Yz=v=>gt+SIG_H*(1-(v-zlo)/(zhi-zlo));
  ctx.fillStyle='rgba(239,83,80,.10)';ctx.fillRect(L,Yz(zhi),R-L,Yz(1)-Yz(zhi));
  ctx.strokeStyle='#222b36';[1,0,-1].forEach(z=>{ctx.beginPath();
    ctx.moveTo(L,Yz(z));ctx.lineTo(R,Yz(z));ctx.stroke();
    ctx.fillStyle='#8b949e';ctx.fillText(z.toFixed(0),R+6,Yz(z)+3)});
  ctx.strokeStyle='#e3b341';ctx.lineWidth=1.2;ctx.beginPath();st=false;
  for(let i=Math.floor(s);i<e&&i<n;i++){if(p.volz[i]==null){st=false;continue;}
    const x=X(i),y=Yz(Math.max(zlo,Math.min(zhi,p.volz[i])));
    if(!st){ctx.moveTo(x,y);st=true}else ctx.lineTo(x,y)}
  ctx.stroke();ctx.lineWidth=1;label(L,gt+11,'z realized_var (vol)');
  // ---- crosshair ----
  if(hover!=null&&hover>=s&&hover<e){const x=X(hover);
    ctx.strokeStyle='#566';ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(x,16);ctx.lineTo(x,zb);ctx.stroke();ctx.setLineDash([])}
  legend(p,(hover==null||hover<s||hover>=e)?Math.min(n-1,Math.floor(e)-1):hover);}

function tri(x,y,r,up){ctx.beginPath();if(up){ctx.moveTo(x,y-r);ctx.lineTo(x-r,y+r);
  ctx.lineTo(x+r,y+r)}else{ctx.moveTo(x,y+r);ctx.lineTo(x-r,y-r);ctx.lineTo(x+r,y-r)}
  ctx.closePath();ctx.fill()}
function grid(L,R,hi,lo,Y,fmt){ctx.strokeStyle='#222b36';ctx.fillStyle='#8b949e';
  for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,y=Y(v);ctx.beginPath();
    ctx.moveTo(L,y);ctx.lineTo(R,y);ctx.stroke();ctx.fillText(fmt(v),R+6,y+3)}}
function label(x,y,t){ctx.fillStyle='#8b949e';ctx.fillText(t,x+4,y)}

function legend(p,i){const el=document.getElementById('legend');
  const z=p.volz[i];let tag='';
  if(z!=null)tag = z>=1?'<span class="pill hot">VOL RIDICATA</span>'
              : z<=-1?'<span class="pill cold">VOL SCAZUTA</span>':'';
  const f=(x,d=2)=>x==null?'–':x.toFixed(d);
  el.innerHTML=`<b>${p.symbol}</b> ${p.dates[i]} &nbsp; O <b>${f(p.o[i])}</b>
    H <b>${f(p.h[i])}</b> L <b>${f(p.l[i])}</b>
    C <b class="${p.c[i]>=p.o[i]?'up':'down'}">${f(p.c[i])}</b>
    &nbsp; <span class="maC">MA50 ${f(p.ma[i])}</span>
    &nbsp; Vol ${p.v[i]==null?'–':(p.v[i]/1e6).toFixed(2)+'M'}
    &nbsp; z=<b>${f(z)}</b> ${tag}`}

// ---- zoom / pan ----
function idxAt(clientX){const r=cv.getBoundingClientRect();const w=cv.clientWidth;
  const L=PAD_L,R=w-PAD_R;const m=view.e-view.s;
  return view.s+(clientX-r.left-L)/(R-L)*m}
cv.addEventListener('mousemove',e=>{if(drag){const r=cv.getBoundingClientRect();
    const w=cv.clientWidth;const L=PAD_L,R=w-PAD_R;const m=view.e-view.s;
    const di=(e.clientX-drag.x)/(R-L)*m;let s=drag.s-di,en=drag.e-di;
    const n=DATA.panels[cur].c.length;if(s<0){en-=s;s=0}if(en>n){s-=en-n;en=n}
    view.s=Math.max(0,s);view.e=Math.min(n,en);hover=null;draw();return}
  hover=Math.round(idxAt(e.clientX));draw()});
cv.addEventListener('mouseleave',()=>{hover=null;draw()});
cv.addEventListener('mousedown',e=>{drag={x:e.clientX,s:view.s,e:view.e};
  cv.style.cursor='grabbing'});
window.addEventListener('mouseup',()=>{drag=null;cv.style.cursor='crosshair'});
cv.addEventListener('wheel',e=>{e.preventDefault();const n=DATA.panels[cur].c.length;
  const c=idxAt(e.clientX);const f=e.deltaY>0?1.15:1/1.15;
  let s=c-(c-view.s)*f,en=c+(view.e-c)*f;
  if(en-s<8){const mid=(s+en)/2;s=mid-4;en=mid+4}
  view.s=Math.max(0,s);view.e=Math.min(n,en);hover=null;draw()},{passive:false});
cv.addEventListener('dblclick',()=>{const n=DATA.panels[cur].c.length;
  view={s:Math.max(0,n-250),e:n};draw()});
window.addEventListener('resize',draw);
select(0);
</script></body></html>"""
