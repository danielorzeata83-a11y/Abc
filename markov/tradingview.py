"""Trading view HTML self-contained (echivalent TradingView, offline, zero deps
externe). Date incorporate ca JSON + canvas vanilla JS: lumanari OHLC + volum +
sub-panou cu semnalul nostru de volatilitate (z realized_var), crosshair,
comutator de simboluri. Alimentat din cache + motor. NU consiliere de investitii.
"""

import json

import numpy as np

from markov.intraday.bars import resample
from markov.intraday.cache import read_bars
from markov.validation import tier1
from markov.validation.ensemble import zscore_causal

DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare."


def _nan_to_none(a):
    return [None if not np.isfinite(x) else round(float(x), 4) for x in a]


def panel_for_symbol(symbol, bars):
    """Bars -> dict serializabil: dates + OHLCV + seria z realized_var (semnalul nostru)."""
    df = bars.to_frame()
    dates = [str(np.datetime_as_string(t, unit="D")) for t in bars.timestamps]
    volz = zscore_causal(np.asarray(tier1.INDICATORS["realized_var"](bars), dtype=float))
    return {
        "symbol": symbol,
        "dates": dates,
        "o": _nan_to_none(df["open"]), "h": _nan_to_none(df["high"]),
        "l": _nan_to_none(df["low"]), "c": _nan_to_none(df["close"]),
        "v": _nan_to_none(df["volume"]),
        "volz": _nan_to_none(volz),
    }


def collect_panels(symbols, data_dir, horizon_tf="1day", max_bars=750):
    """Citeste cache-ul -> lista de panouri (ultimele max_bars bare). Sare simbolurile
    lipsa din cache."""
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


def build_html(panels, asof, title="Abc — trading view"):
    """Pagina HTML self-contained (date incorporate, fara cereri externe). Cu disclaimer."""
    data_json = json.dumps({"asof": asof, "panels": panels}, separators=(",", ":"))
    return _TEMPLATE.replace("__TITLE__", title).replace(
        "__DISCLAIMER__", DISCLAIMER).replace("__DATA__", data_json)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{--bg:#0e1117;--pane:#161b22;--grid:#222b36;--txt:#c9d1d9;--mut:#8b949e;
        --up:#26a69a;--down:#ef5350;--acc:#e3b341}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
       font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif}
  header{display:flex;align-items:center;gap:14px;padding:10px 16px;
         border-bottom:1px solid var(--grid)}
  header h1{font-size:15px;margin:0;font-weight:600}
  #tabs{display:flex;gap:6px;flex-wrap:wrap}
  .tab{padding:4px 12px;background:var(--pane);border:1px solid var(--grid);
       border-radius:5px;cursor:pointer;color:var(--mut)}
  .tab.on{color:var(--txt);border-color:var(--acc)}
  #legend{padding:6px 16px;color:var(--mut);font-variant-numeric:tabular-nums;
          white-space:nowrap;overflow:auto}
  #legend b{color:var(--txt)} .up{color:var(--up)} .down{color:var(--down)}
  #wrap{padding:0 8px} canvas{width:100%;display:block;cursor:crosshair}
  footer{padding:10px 16px;color:var(--mut);border-top:1px solid var(--grid);font-size:12px}
  .pill{padding:1px 7px;border-radius:9px;font-size:11px}
  .hot{background:rgba(239,83,80,.18);color:var(--down)}
  .cold{background:rgba(38,166,154,.18);color:var(--up)}
</style></head><body>
<header><h1>__TITLE__</h1><div id="tabs"></div><span id="asof" style="color:var(--mut)"></span></header>
<div id="legend"></div>
<div id="wrap"><canvas id="cv"></canvas></div>
<footer>Sub-panou: <b>z realized_var</b> — semnalul de volatilitate al motorului
(praguri ±1; rosu = vol ridicata = risc forward mai mare). __DISCLAIMER__</footer>
<script>
const DATA = __DATA__;
document.getElementById('asof').textContent = 'pana la ' + DATA.asof;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
let cur=0, hover=null, DPR=window.devicePixelRatio||1;
const PRICE_H=380, VOL_H=70, SIG_H=110, PAD_L=8, PAD_R=64, GAP=8;
const TOTAL_H=PRICE_H+VOL_H+SIG_H+2*GAP;

function tabs(){const t=document.getElementById('tabs');t.innerHTML='';
  DATA.panels.forEach((p,i)=>{const d=document.createElement('div');
    d.className='tab'+(i===cur?' on':'');d.textContent=p.symbol;
    d.onclick=()=>{cur=i;hover=null;tabs();draw()};t.appendChild(d)})}

function dims(){const w=cv.clientWidth;cv.width=w*DPR;cv.height=TOTAL_H*DPR;
  cv.style.height=TOTAL_H+'px';ctx.setTransform(DPR,0,0,DPR,0,0);return w}

function draw(){const w=dims();const p=DATA.panels[cur];const n=p.c.length;
  const L=PAD_L,R=w-PAD_R;const bw=Math.max(1,(R-L)/n*0.7);
  ctx.clearRect(0,0,w,TOTAL_H);
  // ---- price pane ----
  let hi=-1e18,lo=1e18;for(let i=0;i<n;i++){if(p.h[i]!=null)hi=Math.max(hi,p.h[i]);
    if(p.l[i]!=null)lo=Math.min(lo,p.l[i])}
  const sp=(hi-lo)||1;hi+=sp*0.04;lo-=sp*0.04;
  const X=i=>L+(R-L)*(i+0.5)/n;
  const Yp=v=>16+(PRICE_H-24)*(1-(v-lo)/(hi-lo));
  grid(L,R,16,16+PRICE_H-8,hi,lo,Yp,v=>v.toFixed(2));
  for(let i=0;i<n;i++){if(p.c[i]==null)continue;const up=p.c[i]>=p.o[i];
    ctx.strokeStyle=ctx.fillStyle=up?'#26a69a':'#ef5350';
    ctx.beginPath();ctx.moveTo(X(i),Yp(p.h[i]));ctx.lineTo(X(i),Yp(p.l[i]));ctx.stroke();
    const y1=Yp(p.o[i]),y2=Yp(p.c[i]);
    ctx.fillRect(X(i)-bw/2,Math.min(y1,y2),bw,Math.max(1,Math.abs(y2-y1)))}
  // ---- volume pane ----
  const vt=16+PRICE_H+GAP;let vmax=0;for(let i=0;i<n;i++)if(p.v[i]!=null)vmax=Math.max(vmax,p.v[i]);
  for(let i=0;i<n;i++){if(p.v[i]==null)continue;const up=p.c[i]>=p.o[i];
    ctx.fillStyle=up?'rgba(38,166,154,.5)':'rgba(239,83,80,.5)';
    const h=(VOL_H-6)*(p.v[i]/(vmax||1));ctx.fillRect(X(i)-bw/2,vt+VOL_H-h,bw,h)}
  label(L,vt+11,'Volum');
  // ---- signal pane (z realized_var) ----
  const st=vt+VOL_H+GAP;const zb=st+SIG_H;
  const zhi=3,zlo=-3;const Yz=v=>st+(SIG_H)*(1-(v-zlo)/(zhi-zlo));
  ctx.fillStyle='rgba(239,83,80,.10)';ctx.fillRect(L,Yz(zhi),R-L,Yz(1)-Yz(zhi));
  ctx.strokeStyle='#222b36';[1,0,-1].forEach(z=>{ctx.beginPath();
    ctx.moveTo(L,Yz(z));ctx.lineTo(R,Yz(z));ctx.stroke();
    ctx.fillStyle='#8b949e';ctx.fillText(z.toFixed(0),R+6,Yz(z)+3)});
  ctx.strokeStyle='#e3b341';ctx.lineWidth=1.2;ctx.beginPath();let started=false;
  for(let i=0;i<n;i++){if(p.volz[i]==null){started=false;continue;}
    const x=X(i),y=Yz(Math.max(zlo,Math.min(zhi,p.volz[i])));
    if(!started){ctx.moveTo(x,y);started=true}else ctx.lineTo(x,y)}
  ctx.stroke();ctx.lineWidth=1;label(L,st+11,'z realized_var (vol)');
  // ---- crosshair ----
  if(hover!=null&&hover>=0&&hover<n){const x=X(hover);
    ctx.strokeStyle='#566';ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(x,16);ctx.lineTo(x,zb);ctx.stroke();ctx.setLineDash([])}
  legend(p,hover==null?n-1:hover);}

function grid(L,R,top,bot,hi,lo,Y,fmt){ctx.strokeStyle='#222b36';ctx.fillStyle='#8b949e';
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
    &nbsp; Vol ${p.v[i]==null?'–':(p.v[i]/1e6).toFixed(2)+'M'}
    &nbsp; z=<b>${f(z)}</b> ${tag}`}

cv.addEventListener('mousemove',e=>{const r=cv.getBoundingClientRect();
  const p=DATA.panels[cur];const n=p.c.length;const w=cv.clientWidth;
  const L=PAD_L,R=w-PAD_R;const i=Math.floor((e.clientX-r.left-L)/(R-L)*n);
  hover=Math.max(0,Math.min(n-1,i));draw()});
cv.addEventListener('mouseleave',()=>{hover=null;draw()});
window.addEventListener('resize',draw);
tabs();draw();
</script></body></html>"""
