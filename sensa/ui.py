"""Shared page shell (navigation + theme) and the institutional-manager pages.

Own markup/CSS/JS, written from scratch. Page JS builds DOM with textContent only
(no innerHTML), and every link target is either a constant or a validated number."""

BASE_CSS = r"""
:root{--bg:#060d19;--card:#0a1527;--card2:#0d1b31;--line:#16263f;--fg:#e8eefb;--mut:#8497b5;
--up:#22c58b;--dn:#f0524f;--acc:#1677ff;--acc2:#19c7a5}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.nav{display:flex;align-items:center;gap:.25rem;padding:.55rem 1.25rem;border-bottom:1px solid var(--line);
background:#07101f;position:sticky;top:0;z-index:5}
.nav .brand{font-weight:800;font-size:1.05rem;margin-right:1.2rem;letter-spacing:.02em}
.nav .brand i{font-style:normal;color:var(--acc2)}
.nav a.item{color:var(--mut);padding:.4rem .75rem;border-radius:8px;font-weight:600}
.nav a.item:hover{color:var(--fg);background:var(--card);text-decoration:none}
.nav a.item.on{color:var(--fg);background:var(--card2)}
.wrap{max-width:1360px;margin:0 auto;padding:1rem 1.25rem 2rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem;min-width:0}
.card h3{margin:0 0 .7rem;font-size:.95rem}
.mut{color:var(--mut)}.up{color:var(--up)}.dn{color:var(--dn)}
.btn{background:var(--card2);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.3rem .8rem;cursor:pointer;font:inherit}
.btn.on{background:var(--acc);border-color:var(--acc);color:#fff}
.btn:disabled{opacity:.4;cursor:default}
.err{color:var(--dn);font-size:.9rem}
footer.foot{color:var(--mut);font-size:.75rem;padding:1rem 1.25rem;border-top:1px solid var(--line)}
@media(max-width:700px){.nav{padding:.5rem .6rem;overflow-x:auto}.wrap{padding:.7rem}}
"""

NAV_ITEMS = (("dash", "/", "Dashboard"), ("smart", "/smart-money", "Smart Money"),
             ("inst", "/institutional-investor", "Funds"), ("insider", "/inside-trade", "Insiders"), ("dark", "/dark-pool", "Dark pool"), ("political", "/political-trades", "Politicians"),
             ("alerts", "/smart-money/alerts", "Alerts"))


def nav(active):
    items = "".join(f'<a class="item{" on" if k == active else ""}" href="{h}">{t}</a>'
                    for k, h, t in NAV_ITEMS)
    return f'<nav class="nav"><span class="brand">Options<i>Dash</i></span>{items}</nav>'


def shell(title, active, body, script="", extra_css=""):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>{BASE_CSS}{extra_css}</style></head><body>'
            f'{nav(active)}{body}'
            f'<footer class="foot">Research artifact - not investment advice. '
            f'13F data: SEC EDGAR. Tickers: OpenFIGI.</footer>'
            f'<script>{script}</script></body></html>')


# ---------------------------------------------------------------- manager page
_MANAGER_CSS = r"""
.crumb{color:var(--mut);margin-bottom:.8rem}.crumb b{color:var(--fg);font-weight:600}
h1.title{font-size:2.3rem;margin:.1rem 0 .4rem;letter-spacing:-.01em}
.badges span{font-size:.65rem;font-weight:700;letter-spacing:.06em;padding:.15rem .5rem;border-radius:999px;
background:#0f2a52;color:#5aa2ff;margin-right:.4rem;text-transform:uppercase}
.meta{display:flex;flex-wrap:wrap;gap:.4rem 1.6rem;margin:.7rem 0 1.1rem}
.meta div span{display:block;font-size:.62rem;letter-spacing:.08em;color:var(--mut);text-transform:uppercase}
.meta div b{font-weight:600}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.9rem;margin-bottom:1rem}
.stat .k{font-size:.62rem;letter-spacing:.08em;color:var(--mut);text-transform:uppercase}
.stat .v{font-size:1.9rem;font-weight:800;margin:.3rem 0 .1rem}.stat .d{font-size:.75rem}
.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:1rem;align-items:start}
@media(max-width:1000px){.grid{grid-template-columns:1fr}}
.col{display:flex;flex-direction:column;gap:1rem;min-width:0}
.head{display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem;gap:.5rem;flex-wrap:wrap}
.head h3{margin:0}.seg{display:flex;gap:.25rem}
.tops{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.6rem}
.top{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:.7rem}
.top b{font-size:1.05rem}.top .bar{height:4px;background:var(--line);border-radius:2px;margin-top:.5rem}
.top .bar i{display:block;height:100%;background:var(--acc);border-radius:2px}
table.t{width:100%;border-collapse:collapse}
table.t th{font-size:.7rem;letter-spacing:.05em;color:var(--mut);text-transform:uppercase;text-align:left;padding:.5rem .4rem;font-weight:600}
table.t td{padding:.55rem .4rem;border-top:1px solid var(--line);white-space:nowrap}
.tbl{overflow-x:auto}
.chip.pill{background:#0f2a52;color:#5aa2ff;font-size:.62rem;letter-spacing:.04em}
.chip{display:inline-block;background:#12233d;border-radius:5px;padding:.1rem .4rem;margin-right:.25rem;font-size:.72rem;font-weight:600}
.pager{display:flex;justify-content:space-between;align-items:center;margin-top:.6rem;color:var(--mut);font-size:.8rem}
.alloc-row{display:flex;align-items:center;gap:.6rem;padding:.4rem 0;border-top:1px solid var(--line)}
.alloc-row .sw{width:9px;height:9px;border-radius:2px;flex:none}
.alloc-row .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--mut);font-size:.78rem}
.alloc-row .tk{font-weight:700;width:3.6rem;flex:none}.alloc-row .w{font-variant-numeric:tabular-nums}
.act{display:flex;gap:.7rem;align-items:center;padding:.55rem 0;border-top:1px solid var(--line)}
.act i{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;font-style:normal;font-weight:700;flex:none;background:var(--card2)}
svg text{fill:var(--mut);font-size:11px}
"""

_MANAGER_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/institutional-investor">Institutional</a> &nbsp;›&nbsp; <b id="crumb">…</b></div>
 <h1 class="title" id="name">Loading…</h1>
 <div class="badges"><span>Institutional</span><span>13F filer</span></div>
 <div class="meta">
  <div><span>Location</span><b id="loc">-</b></div>
  <div><span>CIK</span><b id="cikv">__CIK__</b></div>
  <div><span>Most recent</span><b id="recent">-</b></div>
  <div><span>SEC filings</span><a id="sec" target="_blank" rel="noopener noreferrer">View on sec.gov ↗</a></div>
  <div><span>Alerts</span><button class="btn" id="follow" hidden>Follow</button></div>
 </div>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <div class="grid">
  <div class="col">
   <section class="card"><div class="head"><h3>Portfolio Value Over Time</h3><div class="seg" id="ranges"></div></div>
    <div id="chart"></div></section>
   <section class="card"><h3>Top Holdings</h3><div class="tops" id="tops"></div></section>
   <section class="card"><div class="head"><h3>13F Filing History <span class="chip" id="cnt"></span></h3></div>
    <div class="tbl"><table class="t"><thead><tr><th>Quarter</th><th>Holdings</th><th>Value</th>
     <th>Top Holdings</th><th>Form</th><th>Date Filed</th><th>Filing ID</th></tr></thead>
     <tbody id="rows"></tbody></table></div>
    <div class="pager"><span>Rows per page 20</span><span id="pg"></span>
     <span><button class="btn" id="prev">‹</button> <button class="btn" id="next">›</button></span></div></section>
  </div>
  <div class="col">
   <section class="card"><h3>Portfolio Allocation</h3><div id="donut"></div><div id="alloc"></div></section>
   <section class="card"><h3 id="acth">Recent Activity</h3><div id="act"></div></section>
  </div>
 </div>
</div>
"""

_MANAGER_JS = r"""
const CIK="__CIK__",PAGE=20,$=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const money=v=>v==null?'-':Math.abs(v)>=1e9?'$'+(v/1e9).toFixed(2)+'B':Math.abs(v)>=1e6?'$'+(v/1e6).toFixed(2)+'M':'$'+Math.round(v).toLocaleString();
const fdate=d=>new Date(d+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const sgn=v=>(v>0?'+':v<0?'-':'')+money(Math.abs(v));
const PAL=['#1fa3ff','#22c58b','#a78bfa','#ffa64d','#f0524f','#ff7ac6','#4dd6ff','#e6c34b','#7d8cff','#5ee0a0'];
async function api(p){const r=await fetch(p),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
let rows=[],total=0,offset=0,range=20,header=null;
function stat(k,v,d,cls){const c=el('div',null,'card stat');c.append(el('div',k,'k'),el('div',v,'v'),el('div',d,'d '+(cls||'mut')));return c}
function drawHeader(m){header=m;const s=m.stats;
 $('name').textContent=m.name;$('crumb').textContent=m.name;document.title=m.name+' - 13F holdings';
 $('loc').textContent=m.location||'-';$('recent').textContent=m.latest.quarter;
 $('sec').href='https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK='+encodeURIComponent(m.cik)+'&type=13F-HR';
 $('cnt').textContent=s.filings+(s.filings>=40?'+':'');
 const up=s.value_change>=0;
 $('stats').replaceChildren(
  stat('Portfolio value',money(s.value),s.value_change==null?'-':(up?'↑ ':'↓ ')+sgn(s.value_change)+' ('+(s.value_change_pct>0?'+':'')+s.value_change_pct+'%)',up?'up':'dn'),
  stat('Holdings',String(s.holdings),s.holdings_change==null?'-':(s.holdings_change>=0?'↑ ':'↓ ')+Math.abs(s.holdings_change)+' from prev quarter',s.holdings_change>=0?'up':'dn'),
  stat('Filing history',s.filings+(s.filings>=40?'+':''),'Since '+s.since),
  stat('Latest filing',fdate(m.latest.filed),m.latest.form+' · '+m.latest.quarter));
 const t=$('tops');t.replaceChildren();
 for(const h of m.top){const d=el('div',null,'top'),b=el('div',null,'bar'),i=el('i');i.style.width=Math.min(h.weight,100)+'%';b.append(i);
  d.append(el('b',h.ticker),el('div',money(h.value),'mut'),el('div',h.weight+'% of portfolio','mut'),b);t.append(d)}
 drawAlloc(m);drawAct(m)}
function drawAlloc(m){const box=$('donut');box.replaceChildren();const ns='http://www.w3.org/2000/svg',R=64,C=2*Math.PI*R;
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 180 180');svg.setAttribute('width','100%');svg.style.maxHeight='220px';
 let acc=0;const tot=m.allocation.reduce((a,x)=>a+x.weight,0),rest=Math.max(0,100-tot);
 const segs=m.allocation.map((x,i)=>[x.weight,PAL[i%PAL.length]]).concat(rest>0.05?[[rest,'#33445f']]:[]);
 for(const [w,col] of segs){const c=document.createElementNS(ns,'circle');c.setAttribute('cx',90);c.setAttribute('cy',90);c.setAttribute('r',R);
  c.setAttribute('fill','none');c.setAttribute('stroke',col);c.setAttribute('stroke-width',22);
  c.setAttribute('stroke-dasharray',(w/100*C)+' '+C);c.setAttribute('stroke-dashoffset',-acc/100*C);c.setAttribute('transform','rotate(-90 90 90)');svg.append(c);acc+=w}
 const t1=document.createElementNS(ns,'text');t1.setAttribute('x',90);t1.setAttribute('y',92);t1.setAttribute('text-anchor','middle');
 t1.style.fill='#e8eefb';t1.style.fontSize='17px';t1.style.fontWeight='700';t1.textContent=money(m.stats.value);
 const t2=document.createElementNS(ns,'text');t2.setAttribute('x',90);t2.setAttribute('y',108);t2.setAttribute('text-anchor','middle');t2.textContent=m.stats.holdings+' holdings';
 svg.append(t1,t2);box.append(svg);
 const a=$('alloc');a.replaceChildren();
 m.allocation.forEach((x,i)=>{const r=el('div',null,'alloc-row'),sw=el('span',null,'sw');sw.style.background=PAL[i%PAL.length];
  r.append(sw,el('span',x.ticker,'tk'),el('span',x.name,'nm'),el('span',x.weight.toFixed(2)+'%','w'));a.append(r)})}
function drawAct(m){const a=m.activity,A=$('act');A.replaceChildren();
 $('acth').textContent='Recent Activity ('+m.latest.quarter+')';
 for(const [n,txt,sym,cls] of [[a.new,'new position'+(a.new==1?'':'s')+' added','+','up'],[a.increased,'position'+(a.increased==1?'':'s')+' increased','↑','up'],
  [a.reduced,'position'+(a.reduced==1?'':'s')+' reduced','↓','dn'],[a.exited,'position'+(a.exited==1?'':'s')+' exited','✕','dn']]){
  const r=el('div',null,'act'),i=el('i',sym,cls);const d=el('div');d.append(el('b',n+' '+txt),el('div','vs prior quarter','mut'));r.append(i,d);A.append(r)}}
function drawRows(){const tb=$('rows');tb.replaceChildren();
 for(const r of rows.slice(offset,offset+PAGE)){const tr=el('tr'),q=el('td',r.quarter);q.style.fontWeight='700';
  const tp=el('td');for(const t of r.top)tp.append(el('span',t,'chip'));
  const id=el('td'),a=el('a',r.accession.replace(/-/g,''));
  a.href='https://www.sec.gov/Archives/edgar/data/'+parseInt(CIK,10)+'/'+r.accession.replace(/-/g,'')+'/';a.target='_blank';a.rel='noopener noreferrer';id.append(a);
  const fm=el('span',r.form,'chip pill');tr.append(q,el('td',String(r.holdings)),el('td',money(r.value)),tp,(()=>{const c=el('td');c.append(fm);return c})(),el('td',fdate(r.filed)),id);tb.append(tr)}
 $('pg').textContent=(offset+1)+' – '+Math.min(offset+PAGE,total)+' of '+total;
 $('prev').disabled=offset===0;$('next').disabled=offset+PAGE>=total}
function drawChart(){const pts=rows.slice(0,range).slice().reverse(),box=$('chart');
 if(pts.length<2){box.replaceChildren(el('div','Not enough history','mut'));return}
 const W=720,H=260,L=56,B=26,T=10,max=Math.max(...pts.map(p=>p.value))*1.05,ns='http://www.w3.org/2000/svg';
 const X=i=>L+i*(W-L-8)/(pts.length-1),Y=v=>T+(H-T-B)*(1-v/max);
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('width','100%');
 const mk=(n,at)=>{const e=document.createElementNS(ns,n);for(const k in at)e.setAttribute(k,at[k]);return e};
 for(let g=0;g<=4;g++){const v=max*g/4,y=Y(v);svg.append(mk('line',{x1:L,x2:W-8,y1:y,y2:y,stroke:'#16263f'}));
  const t=mk('text',{x:L-6,y:y+4,'text-anchor':'end'});t.textContent=money(v).replace(/\.\d+/,'');svg.append(t)}
 const d=pts.map((p,i)=>(i?'L':'M')+X(i)+' '+Y(p.value)).join(' ');
 svg.append(mk('path',{d:d+' L'+X(pts.length-1)+' '+Y(0)+' L'+X(0)+' '+Y(0)+' Z',fill:'rgba(22,119,255,.12)'}));
 svg.append(mk('path',{d,fill:'none',stroke:'#1677ff','stroke-width':2}));
 const step=Math.max(1,Math.ceil(pts.length/8));
 pts.forEach((p,i)=>{const last=pts.length-1;if((i%step===0&&last-i>=step/2+0.5)||i===last){const t=mk('text',{x:X(i),y:H-8,'text-anchor':i===last?'end':'middle'});t.textContent=p.quarter;svg.append(t)}});
 box.replaceChildren(svg)}
const CHUNK=5;
async function loadPage(off){let o=off;
 while(o<off+PAGE&&(total===0||o<total)){
  if(!rows[o]){const r=await api('/api/manager/'+CIK+'/filings?offset='+o+'&limit='+CHUNK);total=r.total;
   r.rows.forEach((x,i)=>{rows[o+i]=x});if(!r.rows.length)break;drawRows();drawChart()}
  o+=CHUNK}}
async function show(off){try{offset=off;await loadPage(off);drawRows();drawChart()}catch(e){$('msg').textContent=e.message}}
async function setRange(n,btn){range=n;document.querySelectorAll('#ranges .btn').forEach(b=>b.classList.toggle('on',b===btn));
 try{for(let o=0;o<Math.min(n,total||PAGE);o+=PAGE){if(!rows[o])await loadPage(o)}drawChart()}catch(e){$('msg').textContent=e.message}}
for(const [lab,n] of [['3Y',12],['5Y',20],['10Y',40],['All',1000]]){const b=el('button',lab,'btn'+(n===20?' on':''));b.onclick=()=>setRange(n,b);$('ranges').append(b)}
$('prev').onclick=()=>show(Math.max(0,offset-PAGE));$('next').onclick=()=>show(offset+PAGE);
const loadingRow=()=>{const tr=el('tr'),td=el('td','Loading filings…','mut');td.colSpan=7;tr.append(td);$('rows').replaceChildren(tr);$('chart').replaceChildren(el('div','Loading…','mut'))};
loadingRow();
let followed=false;
function drawFollow(){const b=$('follow');b.hidden=false;b.textContent=followed?'Following ✓':'Follow';b.classList.toggle('on',followed)}
async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),j=await r.json();
 if(!r.ok)throw new Error(j.error||r.status);return j}
fetch('/api/watch').then(r=>r.ok?r.json():null).then(w=>{if(!w)return;followed=w.following.some(f=>f.cik===CIK);drawFollow()}).catch(()=>{});
$('follow').onclick=async()=>{try{await post('/api/watch/'+(followed?'unfollow':'follow'),{cik:CIK});followed=!followed;drawFollow()}catch(e){$('msg').textContent=e.message}};
api('/api/manager/'+CIK).then(drawHeader).catch(e=>{$('name').textContent='Manager not available';$('msg').textContent=e.message});
show(0);
setInterval(()=>api('/api/manager/'+CIK).then(drawHeader).catch(()=>{}),600000);   // header stays current
"""


def render_manager(cik10):
    body = _MANAGER_BODY.replace("__CIK__", cik10)
    return shell("13F manager", "inst", body, _MANAGER_JS.replace("__CIK__", cik10), _MANAGER_CSS)


# ------------------------------------------------------------- landing / search
EXAMPLES = (("0001067983", "berkshire-hathaway-inc", "Berkshire Hathaway Inc"),
            ("0001649339", "scion-asset-management-llc", "Scion Asset Management LLC"),
            ("0001350694", "bridgewater-associates-lp", "Bridgewater Associates LP"),
            ("0001336528", "pershing-square-capital-management-lp", "Pershing Square Capital Management LP"),
            ("0001609098", "darsana-capital-partners-lp", "Darsana Capital Partners LP"))

_INST_BODY = r"""
<div class="wrap">
 <h1 class="title">Institutional investors</h1>
 <p class="mut">Open any 13F filer by CIK. Holdings, history and quarter-over-quarter activity come from SEC filings.</p>
 <form id="f" class="card" style="display:flex;gap:.6rem;flex-wrap:wrap;margin:1rem 0">
  <input id="cik" inputmode="numeric" placeholder="CIK, e.g. 1067983" aria-label="CIK"
   style="flex:1;min-width:180px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.5rem .7rem;font:inherit">
  <button class="btn on" type="submit">Open</button><span id="e" class="err"></span>
 </form>
 <form id="tkf" class="card" style="display:flex;gap:.6rem;flex-wrap:wrap;margin:0 0 1rem;align-items:center">
  <b>Who holds a stock?</b>
  <input id="tk" placeholder="Ticker, e.g. AAPL" maxlength="10" aria-label="Ticker"
   style="flex:1;min-width:160px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.5rem .7rem;font:inherit;text-transform:uppercase">
  <button class="btn on" type="submit">Investors</button><span id="te" class="err"></span>
 </form>
 <section class="card"><h3>Browse</h3><p style="margin:.2rem 0 .8rem"><a href="/institutional-investor/latest-filings">Latest 13F filings →</a></p>
  <div class="letters">__LETTERS__</div></section>
 <section class="card" style="margin-top:1rem"><h3>Examples</h3>__EXAMPLES__</section>
</div>
"""

_INST_JS = r"""
document.getElementById('f').onsubmit=e=>{e.preventDefault();
 const v=document.getElementById('cik').value.trim().replace(/^0+/,'');
 if(!/^[0-9]{1,10}$/.test(v)){document.getElementById('e').textContent='CIK must be 1-10 digits';return}
 location.href='/institutional-investor/manager/'+v.padStart(10,'0')};
document.getElementById('tkf').onsubmit=e=>{e.preventDefault();const v=document.getElementById('tk').value.trim().toUpperCase();
 if(!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(v)){document.getElementById('te').textContent='Enter a ticker, e.g. AAPL';return}
 location.href='/stock/'+encodeURIComponent(v)+'/investors'};
"""


def render_institutional():
    items = "".join(f'<div style="padding:.45rem 0;border-top:1px solid var(--line)">'
                    f'<a href="/institutional-investor/manager/{c}-{slug}">{name}</a> '
                    f'<span class="mut">CIK {c}</span></div>' for c, slug, name in EXAMPLES)
    letters = "".join(f'<a href="/institutional-investor/managers/{c}">{"#" if c == "0" else c.upper()}</a>'
                      for c in "abcdefghijklmnopqrstuvwxyz0")
    body = _INST_BODY.replace("__EXAMPLES__", items).replace("__LETTERS__", letters)
    return shell("Institutional investors", "inst", body, _INST_JS, _MANAGER_CSS + _LIST_CSS)


# ------------------------------------------------------------------ alerts page
_ALERTS_CSS = r"""
.ev{padding:.8rem 0;border-top:1px solid var(--line)}.ev:first-child{border-top:0}
.ev .top{display:flex;justify-content:space-between;gap:.6rem;flex-wrap:wrap}
.ev .cnt span{margin-right:.9rem}.ev ul{margin:.4rem 0 0;padding-left:1.1rem;color:var(--mut);font-size:.82rem}
.tag{font-size:.65rem;font-weight:700;letter-spacing:.05em;border-radius:5px;padding:.05rem .4rem;margin-right:.4rem}
.tag.new{background:#0c3b2c;color:#22c58b}.tag.exited{background:#451a1a;color:#f0524f}
.tag.increased{background:#10305c;color:#5aa2ff}.tag.reduced{background:#4a3410;color:#ffb347}
.row{display:flex;justify-content:space-between;align-items:center;padding:.45rem 0;border-top:1px solid var(--line)}
"""

_ALERTS_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Smart Money alerts</h1>
 <p class="mut">Follow funds and get a signal when they file a new 13F: positions added, removed, increased or reduced.
 13F reports are quarterly (due 45 days after quarter end), so a signal arrives when SEC publishes the filing.</p>
 <div id="msg" class="err"></div>
 <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:1rem;align-items:start" id="g">
  <section class="card"><h3>Following</h3>
   <form id="f" style="display:flex;gap:.5rem;margin-bottom:.6rem">
    <input id="cik" inputmode="numeric" placeholder="CIK" aria-label="CIK"
     style="flex:1;min-width:0;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.45rem .6rem;font:inherit">
    <button class="btn on" type="submit">Follow</button></form>
   <div id="fl"></div>
   <button class="btn" id="chk" style="margin-top:.8rem">Check now</button> <span id="st" class="mut"></span>
  </section>
  <section class="card"><h3>Recent signals</h3><div id="ev"></div></section>
 </div>
</div>
"""

_ALERTS_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const money=v=>Math.abs(v)>=1e9?'$'+(v/1e9).toFixed(2)+'B':Math.abs(v)>=1e6?'$'+(v/1e6).toFixed(1)+'M':'$'+Math.round(v).toLocaleString();
async function api(p,body){const r=await fetch(p,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined),j=await r.json();
 if(!r.ok)throw new Error(j.error||r.status);return j}
function draw(w){const fl=$('fl');fl.replaceChildren();
 if(!w.following.length)fl.append(el('div','Not following any fund yet. Enter a CIK, e.g. 1067983 (Berkshire) or 1609098.','mut'));
 for(const f of w.following){const r=el('div',null,'row'),a=el('a',f.name||f.cik);a.href='/institutional-investor/manager/'+f.cik;
  const b=el('button','Unfollow','btn');b.onclick=async()=>{try{draw(await api('/api/watch/unfollow',{cik:f.cik}))}catch(e){$('msg').textContent=e.message}};r.append(a,b);fl.append(r)}
 const ev=$('ev');ev.replaceChildren();
 if(!w.events||!w.events.length)ev.append(el('div','No signals yet. They appear here when a followed fund files a new 13F.','mut'));
 for(const e of (w.events||[])){const d=el('div',null,'ev'),top=el('div',null,'top'),a=el('a',e.name);a.href='/institutional-investor/manager/'+e.cik;
  top.append(a,el('span',e.quarter+' · '+e.form+(e.amended?' (amended)':'')+' · filed '+e.filed,'mut'));
  const c=el('div',null,'cnt');for(const k of ['new','exited','increased','reduced']){c.append(el('span',e.counts[k]+' '+k))}
  const ul=el('ul');for(const ch of e.changes.slice(0,8)){const li=el('li');li.append(el('span',ch.type.toUpperCase(),'tag '+ch.type),
    document.createTextNode(ch.ticker+' '+money(ch.type==='exited'?ch.value_prev:ch.value_now)+' ('+(ch.shares_now-ch.shares_prev>=0?'+':'')+Math.round(ch.shares_now-ch.shares_prev).toLocaleString()+' sh)'));ul.append(li)}
  d.append(top,c,ul);ev.append(d)}}
async function load(){try{draw(await api('/api/watch'));$('msg').textContent=''}catch(e){$('msg').textContent=e.message}}
$('f').onsubmit=async e=>{e.preventDefault();const v=$('cik').value.trim().replace(/^0+/,'');
 if(!/^[0-9]{1,10}$/.test(v)){$('msg').textContent='CIK must be 1-10 digits';return}
 try{$('msg').textContent='';draw(Object.assign(await api('/api/watch/follow',{cik:v}),{events:(await api('/api/watch')).events}));$('cik').value=''}catch(er){$('msg').textContent=er.message}};
$('chk').onclick=async()=>{$('st').textContent='checking…';try{const r=await api('/api/watch/check',{});$('st').textContent=r.new_events+' new signal(s)';load()}catch(e){$('st').textContent='';$('msg').textContent=e.message}};
load();setInterval(load,60000);
"""


def render_alerts():
    return shell("Smart Money alerts", "alerts", _ALERTS_BODY, _ALERTS_JS, _MANAGER_CSS + _ALERTS_CSS)


# ------------------------------------------------------- Smart Money overview (top 100)
_SM_CSS = r"""
.bar{display:flex;gap:.8rem;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:.8rem 0}
.tabs{display:flex;gap:.4rem;align-items:center;flex-wrap:wrap;margin:1rem 0 .8rem}
select.sel{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.3rem .5rem;font:inherit}
th.s{cursor:pointer;user-select:none}th.s:hover{color:var(--fg)}
td.n,th.n{text-align:right}.note{font-size:.78rem;color:var(--mut);margin:.4rem 0}
.moves{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem}
.mrow{display:flex;justify-content:space-between;gap:.6rem;padding:.4rem 0;border-top:1px solid var(--line)}
.mrow b{margin-right:.4rem}.mrow .r{text-align:right;white-space:nowrap}
"""

_SM_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Smart Money</h1>
 <p class="mut">What the largest 13F filers hold, taken together, and how they moved since the previous quarter.</p>
 <div class="card bar"><span id="st" class="mut">Loading…</span><span><button class="btn" id="upd">Update from SEC</button></span></div>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <div class="tabs" id="tabs"></div>
 <div id="view"></div>
 <p class="note" id="note"></p>
</div>
"""

_SM_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const money=v=>{const a=Math.abs(v),s=a>=1e12?'$'+(a/1e12).toFixed(2)+'T':a>=1e9?'$'+(a/1e9).toFixed(1)+'B':a>=1e6?'$'+(a/1e6).toFixed(0)+'M':'$'+Math.round(a).toLocaleString();return (v<0?'-':'')+s};
const smoney=v=>(v>0?'+':'')+money(v);
const pct=v=>v==null?'-':(v>0?'+':'')+v.toFixed(1)+'%';
const cls=v=>v>0?'up':v<0?'dn':'mut';
async function api(p,body){const r=await fetch(p,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined),j=await r.json();
 if(!r.ok)throw new Error(j.error||r.status);return j}
let O=null,tab='held',kinds='stock',sortKey=null,sortDir=-1;
const okKind=s=>kinds==='all'||s.kind==='stock'||s.kind==='adr';
const core=s=>okKind(s)&&!s.gone&&!s.new_listing;
function table(cols,rows,defKey){const t=el('table',null,'t'),thead=el('thead'),hr=el('tr');
 const key=sortKey&&cols.some(c=>c.k===sortKey)?sortKey:defKey,dir=sortKey&&cols.some(c=>c.k===sortKey)?sortDir:(cols.find(c=>c.k===defKey)||{}).dir||-1;
 for(const c of cols){const th=el('th',c.l+(c.k===key?(dir<0?' ▾':' ▴'):''),(c.n?'n ':'')+(c.sort===false?'':'s'));
  if(c.sort!==false)th.onclick=()=>{sortDir=sortKey===c.k?-sortDir:(c.dir||-1);sortKey=c.k;draw()};hr.append(th)}
 thead.append(hr);t.append(thead);
 const get=r=>{const c=cols.find(c=>c.k===key);return c&&c.v?c.v(r):r[key]};
 const sorted=rows.slice().sort((a,b)=>{const x=get(a),y=get(b);return (x>y?1:x<y?-1:0)*dir});
 const tb=el('tbody');for(const r of sorted.slice(0,100)){const tr=el('tr');for(const c of cols){const td=c.r?c.r(r):el('td',c.f?c.f(r):String(r[c.k]));if(c.n)td.classList.add('n');tr.append(td)}tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
const cell=(txt,c)=>el('td',txt,c);
function heldView(){const rows=O.stocks.filter(s=>okKind(s)&&!s.gone);
 const cols=[{k:'ticker',l:'Ticker',dir:1,r:s=>{const d=el('td');
   if(/^[A-Z][A-Z0-9.\-]{0,9}$/.test(s.ticker)){const a=el('a',s.ticker);a.href='/stock/'+encodeURIComponent(s.ticker)+'/investors';a.style.fontWeight='700';d.append(a)}else d.append(el('b',s.ticker));return d}},
  {k:'issuer',l:'Company',dir:1,f:s=>s.issuer},
  {k:'holders',l:'Funds',n:1,r:s=>cell(s.holders+' / '+O.cohort)},
  {k:'dh',l:'vs last Q',n:1,v:s=>s.holders-s.holders_prev,r:s=>cell((s.holders-s.holders_prev>0?'+':'')+(s.holders-s.holders_prev),cls(s.holders-s.holders_prev))},
  {k:'value',l:'Value',n:1,f:s=>money(s.value)},
  {k:'avg_weight',l:'Avg weight',n:1,f:s=>s.avg_weight.toFixed(2)+'%'},
  {k:'active_flow',l:'Active flow',n:1,r:s=>cell(smoney(s.active_flow),cls(s.active_flow))},
  {k:'added',l:'Added',n:1,f:s=>String(s.added)},{k:'reduced',l:'Reduced',n:1,f:s=>String(s.reduced)},
  {k:'new',l:'New',n:1,f:s=>String(s.new)},{k:'exited',l:'Exited',n:1,f:s=>String(s.exited)}];
 return table(cols,rows,'holders')}
function list(title,rows,right,sub){const c=el('section',null,'card');c.append(el('h3',title));if(sub)c.append(el('div',sub,'note'));
 if(!rows.length)c.append(el('div','Nothing to show','mut'));
 for(const s of rows.slice(0,10)){const r=el('div',null,'mrow'),l=el('span'),b=el('b',s.ticker);l.append(b,document.createTextNode(s.issuer));
  const rr=el('span',null,'r');right(s,rr);r.append(l,rr);c.append(r)}return c}
function movesView(){const st=O.stocks.filter(core),w=el('div',null,'moves');
 const flow=(s,r)=>{r.append(el('span',smoney(s.active_flow),cls(s.active_flow)),el('span','  '+s.holders+'/'+O.cohort,'mut'))};
 w.append(list('Biggest active buying',st.slice().sort((a,b)=>b.active_flow-a.active_flow),flow,'Net shares bought beyond each fund\'s own proportional growth'),
  list('Biggest active selling',st.slice().sort((a,b)=>a.active_flow-b.active_flow),flow),
  list('Most new positions',st.filter(s=>s.new).sort((a,b)=>b.new-a.new),(s,r)=>r.append(el('span','+'+s.new+' funds','up'),el('span','  '+s.holders+'/'+O.cohort,'mut')),'Funds that did not hold it last quarter'),
  list('Most positions closed',st.filter(s=>s.exited).sort((a,b)=>b.exited-a.exited),(s,r)=>r.append(el('span','-'+s.exited+' funds','dn'),el('span','  '+s.holders+'/'+O.cohort,'mut'))),
  list('New to the group',O.stocks.filter(s=>s.new_listing&&okKind(s)).sort((a,b)=>b.holders-a.holders),(s,r)=>r.append(el('span',s.holders+'/'+O.cohort+' funds','up')),'IPOs, spin-offs, mergers and CUSIP changes: not chosen purchases'),
  list('Disappeared from the group',O.stocks.filter(s=>s.gone).sort((a,b)=>b.holders_prev-a.holders_prev),(s,r)=>r.append(el('span',s.holders_prev+' funds held it','mut')),'Held last quarter, now by nobody: usually acquired or delisted, not sold'));
 return w}
function fundsView(){const cols=[{k:'rank',l:'#',dir:1,f:f=>String(f.rank)},
  {k:'name',l:'Fund',dir:1,r:f=>{const d=el('td');if(/^[0-9]{1,10}$/.test(f.cik)){const a=el('a',f.name);a.href='/institutional-investor/manager/'+f.cik;d.append(a)}else d.textContent=f.name;return d}},
  {k:'aum',l:'Reported value',n:1,f:f=>money(f.aum)},
  {k:'aum_change_pct',l:'vs last Q',n:1,v:f=>f.aum_change_pct==null?-1e9:f.aum_change_pct,r:f=>cell(pct(f.aum_change_pct),cls(f.aum_change_pct))},
  {k:'positions',l:'Positions',n:1,f:f=>String(f.positions)},
  {k:'top',l:'Top holdings',sort:false,r:f=>{const d=el('td');for(const t of f.top.slice(0,3))d.append(el('span',t.ticker,'chip'));return d}},
  {k:'top10_pct',l:'Top 10',n:1,f:f=>f.top10_pct.toFixed(1)+'%'},
  {k:'turnover_pct',l:'Turnover',n:1,v:f=>f.turnover_pct==null?-1:f.turnover_pct,f:f=>f.turnover_pct==null?'-':f.turnover_pct.toFixed(1)+'%'},
  {k:'new',l:'New',n:1,v:f=>f.new==null?-1:f.new,f:f=>f.new==null?'-':String(f.new)},
  {k:'exited',l:'Exited',n:1,v:f=>f.exited==null?-1:f.exited,f:f=>f.exited==null?'-':String(f.exited)}];
 return table(cols,O.funds,'rank')}
function draw(){if(!O)return;const v=$('view');
 v.replaceChildren(tab==='held'?heldView():tab==='moves'?movesView():fundsView())}
function drawAll(){$('stats').replaceChildren(
  ...[['Funds in view',String(O.cohort),O.comparable+' comparable with '+O.prev_quarter],['Reported value',money(O.total_aum),O.quarter],
      ['Distinct stocks',O.distinct_stocks.toLocaleString(),'held by at least one of them'],['Stock splits adjusted',String((O.splits||[]).length),'so they do not look like buying']]
   .map(([k,v,d])=>{const c=el('div',null,'card stat');c.append(el('div',k,'k'),el('div',v,'v'),el('div',d,'d mut'));return c}));
 const t=$('tabs');t.replaceChildren();
 for(const [k,l] of [['held','Most held'],['moves','Moves'],['funds','Top funds']]){const b=el('button',l,'btn'+(k===tab?' on':''));b.onclick=()=>{tab=k;sortKey=null;drawAll()};t.append(b)}
 const sel=el('select',null,'sel');for(const [k,l] of [['stock','Stocks & ADRs'],['all','Include ETFs & other']]){const o=el('option',l);o.value=k;o.selected=k===kinds;sel.append(o)}
 sel.onchange=()=>{kinds=sel.value;draw()};if(tab!=='funds')t.append(sel);
 $('note').textContent='Funds = how many of the '+O.cohort+' filers hold it. Active flow = net shares bought or sold beyond each fund\'s own proportional growth, at quarter-end prices. 13F lists long positions only, reported up to 45 days after quarter end.';
 draw()}
async function status(){try{const s=await api('/api/smart-money/status');
  $('st').textContent=s.state==='running'?'Updating from SEC… this can take a few minutes':(s.quarter?'Data: '+s.quarter+' · built '+s.built_at.replace('T',' ').replace('+00:00',' UTC'):'Not built yet')+(s.state==='error'?' · last update failed: '+s.message:'');
  $('upd').disabled=s.state==='running';return s.state}catch(e){$('st').textContent='';return 'idle'}}
async function load(){try{O=await api('/api/smart-money/overview');$('msg').textContent='';drawAll()}catch(e){O=null;$('stats').replaceChildren();$('tabs').replaceChildren();$('view').replaceChildren();$('msg').textContent=e.message}}
async function poll(){const s=await status();if(s==='running')setTimeout(poll,3000);else load()}
$('upd').onclick=async()=>{try{await api('/api/smart-money/refresh',{force:false});poll()}catch(e){$('msg').textContent=e.message}};
load();poll();
"""


def render_smart_money():
    return shell("Smart Money", "smart", _SM_BODY, _SM_JS, _MANAGER_CSS + _SM_CSS)


# --------------------------------------------- managers A-Z, latest filings, one filing
_COMMON_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const money=v=>{if(v==null)return '-';const a=Math.abs(v),s=a>=1e12?'$'+(a/1e12).toFixed(2)+'T':a>=1e9?'$'+(a/1e9).toFixed(2)+'B':a>=1e6?'$'+(a/1e6).toFixed(2)+'M':'$'+Math.round(a).toLocaleString();return (v<0?'-':'')+s};
const fdate=d=>d?new Date(d+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'-';
const isCik=c=>/^[0-9]{1,10}$/.test(c),isAcc=a=>/^[0-9]{10}-[0-9]{2}-[0-9]{6}$/.test(a);
async function api(p,body){const r=await fetch(p,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function mgrLink(name,cik){const d=el('td');if(isCik(cik)){const a=el('a',name);a.href='/institutional-investor/manager/'+cik;d.append(a)}else d.textContent=name;return d}
function accHref(a){return '/institutional-investor/'+a.replace(/-/g,'')}
function stat(k,v,d){const c=el('div',null,'card stat');c.append(el('div',k,'k'),el('div',v,'v'),el('div',d||'','d mut'));return c}
"""

_LIST_CSS = r"""
.letters{display:flex;flex-wrap:wrap;gap:.3rem;margin:.8rem 0}.letters a,.letters b{padding:.25rem .55rem;border-radius:7px;border:1px solid var(--line);background:var(--card)}
.letters b{background:var(--acc);border-color:var(--acc);color:#fff}
input.q{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.45rem .7rem;font:inherit;min-width:240px}
"""

_MANAGERS_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/institutional-investor">Institutional</a> &nbsp;›&nbsp; <b id="crumb">13F filers</b></div>
 <h1 class="title" style="font-size:2rem" id="ttl">13F filers</h1>
 <p class="mut">Institutional investment managers that file Form 13F with the SEC, by name.</p>
 <div class="letters" id="letters"></div>
 <div class="stats" id="stats"></div>
 <div class="head"><input class="q" id="q" placeholder="Search all filers by name" aria-label="Search filers"><span id="msg" class="err"></span></div>
 <section class="card"><div class="tbl"><table class="t"><thead><tr><th>Manager</th><th>Latest filing</th><th class="n">Holdings</th><th class="n">Portfolio value</th></tr></thead>
 <tbody id="rows"></tbody></table></div>
 <div class="pager"><span id="pg"></span><span><button class="btn" id="prev">‹</button> <button class="btn" id="next">›</button></span></div></section>
</div>
"""

_MANAGERS_JS = r"""
const LETTER="__LETTER__",PAGE=50;let offset=0,total=0,query='',timer=null;
for(const l of 'abcdefghijklmnopqrstuvwxyz0'){const x=l===LETTER&&!query?el('b',l==='0'?'#':l.toUpperCase()):el('a',l==='0'?'#':l.toUpperCase());if(x.tagName==='A')x.href='/institutional-investor/managers/'+l;$('letters').append(x)}
async function load(){try{const p='/api/managers?offset='+offset+'&limit='+PAGE+(query?'&q='+encodeURIComponent(query):'&letter='+LETTER);
 const d=await api(p);total=d.total;$('msg').textContent='';
 $('ttl').textContent=query?'Search: '+query:(LETTER==='0'?'#':LETTER.toUpperCase())+' 13F filers';
 $('stats').replaceChildren(stat('Total filers',d.total.toLocaleString()),stat('Combined value',money(d.aum)),stat('Average holdings',String(d.avg_entries)));
 const tb=$('rows');tb.replaceChildren();
 for(const r of d.rows){const tr=el('tr');tr.append(mgrLink(r.name,r.cik),el('td',r.quarter||'-'),el('td',String(r.entries),'n'),el('td',money(r.aum),'n'));tr.children[2].classList.add('n');tr.children[3].classList.add('n');tb.append(tr)}
 if(!d.rows.length){const tr=el('tr'),td=el('td','No filers found','mut');td.colSpan=4;tr.append(td);tb.append(tr)}
 $('pg').textContent=total?(offset+1)+' – '+Math.min(offset+PAGE,total)+' of '+total.toLocaleString():'';
 $('prev').disabled=offset===0;$('next').disabled=offset+PAGE>=total}catch(e){$('msg').textContent=e.message}}
$('prev').onclick=()=>{offset=Math.max(0,offset-PAGE);load()};$('next').onclick=()=>{offset+=PAGE;load()};
$('q').oninput=e=>{clearTimeout(timer);timer=setTimeout(()=>{query=e.target.value.trim();offset=0;load()},250)};
load();
"""

_LATEST_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/institutional-investor">Institutional</a> &nbsp;›&nbsp; <b>Latest filings</b></div>
 <h1 class="title" style="font-size:2rem">Latest 13F filings</h1>
 <p class="mut">Most recent 13F reports on SEC EDGAR, one row per manager, newest first. Refreshed every few minutes.</p>
 <div id="msg" class="err"></div>
 <section class="card"><div class="tbl"><table class="t"><thead><tr><th>Manager</th><th>Period</th><th>Date filed</th><th class="n">Holdings</th><th class="n">Value</th><th></th></tr></thead>
 <tbody id="rows"><tr><td class="mut" colspan="6">Loading…</td></tr></tbody></table></div></section>
</div>
"""

_LATEST_JS = r"""
(async()=>{try{const rows=await api('/api/latest-filings?limit=100'),tb=$('rows');tb.replaceChildren();
 for(const r of rows){const tr=el('tr'),n=mgrLink(r.name,r.cik);n.append(el('div','CIK '+r.cik,'mut'));
  const v=el('td');if(isAcc(r.accession)){const a=el('a','View');a.href=accHref(r.accession);v.append(a)}
  const ent=el('td',r.entries==null?'-':String(r.entries),'n'),val=el('td',money(r.value),'n');ent.classList.add('n');val.classList.add('n');
  tr.append(n,el('td',(r.quarter||'-')+(r.form==='13F-HR/A'?' (amended)':'')),el('td',fdate(r.filed)),ent,val,v);tb.append(tr)}
 }catch(e){$('rows').replaceChildren();$('msg').textContent=e.message}})();
"""

_FILING_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/institutional-investor">Institutional</a> &nbsp;›&nbsp; <a id="mlink">Manager</a> &nbsp;›&nbsp; <b id="crumb">…</b></div>
 <h1 class="title" id="name" style="font-size:2rem">Loading…</h1>
 <div class="badges"><span>Institutional</span><span id="formb">13F</span></div>
 <div class="meta"><div><span>Location</span><b id="loc">-</b></div><div><span>CIK</span><b id="cik">-</b></div>
  <div><span>Date filed</span><b id="filed">-</b></div><div><span>SEC filing</span><a id="sec" target="_blank" rel="noopener noreferrer">View on sec.gov ↗</a></div></div>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <section class="card"><h3 id="hh">Holdings</h3><div class="tbl"><table class="t"><thead><tr><th>Ticker</th><th>Company</th><th class="n">Shares</th><th class="n">Value</th><th class="n">Weight</th><th>Change</th></tr></thead>
 <tbody id="rows"></tbody></table></div><p class="note" id="trunc"></p></section>
 <section class="card" style="margin-top:1rem" id="exitedcard" hidden><h3>Closed since the previous quarter</h3><div id="exited"></div></section>
</div>
"""

_FILING_JS = r"""
const ACC="__ACC__";
(async()=>{try{const d=await api('/api/filing/'+ACC);
 document.title=d.name+' - '+d.quarter+' 13F holdings';
 $('name').textContent=d.name+' · '+d.quarter;$('crumb').textContent=d.quarter;$('formb').textContent=d.form;
 $('loc').textContent=d.location||'-';$('cik').textContent=d.cik;$('filed').textContent=fdate(d.filed);
 if(isCik(d.cik)){$('mlink').href='/institutional-investor/manager/'+d.cik;$('mlink').textContent=d.name}
 if(isCik(d.cik)&&isAcc(d.accession))$('sec').href='https://www.sec.gov/Archives/edgar/data/'+parseInt(d.cik,10)+'/'+d.accession.replace(/-/g,'')+'/';
 const s=d.stats,up=s.value_change>=0;
 $('stats').replaceChildren(stat('Portfolio value',money(s.value),s.value_change==null?'':(up?'↑ ':'↓ ')+money(Math.abs(s.value_change))+' ('+(s.value_change_pct>0?'+':'')+s.value_change_pct+'%) vs '+d.prev_quarter),
  stat('Positions',String(s.positions),s.positions_change==null?'':(s.positions_change>=0?'↑ ':'↓ ')+Math.abs(s.positions_change)+' vs '+d.prev_quarter),
  stat('Period',d.period,d.form),stat('Top position',d.holdings[0]?d.holdings[0].ticker:'-',d.holdings[0]?d.holdings[0].weight+'% of portfolio':''));
 const tb=$('rows');tb.replaceChildren();
 for(const h of d.holdings){const tr=el('tr'),t=el('td'),b=el('b',h.ticker);t.append(b);
  const ch=el('td');if(h.change){const k=h.change.type,sign=h.change.shares_delta>0?'+':'';
   ch.append(el('span',k.toUpperCase(),'chip pill'),document.createTextNode(' '+sign+Math.round(h.change.shares_delta).toLocaleString()+' sh'+(h.change.pct==null?'':' ('+(h.change.pct>0?'+':'')+h.change.pct+'%)')));
   ch.className=k==='new'||k==='increased'?'up':'dn'}else ch.textContent='-';
  const sh=el('td',Math.round(h.shares).toLocaleString(),'n'),va=el('td',money(h.value),'n'),we=el('td',h.weight.toFixed(2)+'%','n');
  tr.append(t,el('td',h.issuer),sh,va,we,ch);tb.append(tr)}
 $('trunc').textContent=d.truncated?'Showing the 100 largest positions.':'';
 if(d.exited.length){$('exitedcard').hidden=false;const box=$('exited');box.replaceChildren();
  for(const x of d.exited.slice(0,20)){const r=el('div',null,'alloc-row');r.append(el('span',x.issuer,'nm'),el('span',money(x.value),'w'));box.append(r)}}
 }catch(e){$('name').textContent='Filing not available';$('msg').textContent=e.message}})();
"""


def render_managers(letter):
    return shell("13F filers", "inst", _MANAGERS_BODY, _COMMON_JS + _MANAGERS_JS.replace("__LETTER__", letter),
                 _MANAGER_CSS + _LIST_CSS)


def render_latest_filings():
    return shell("Latest 13F filings", "inst", _LATEST_BODY, _COMMON_JS + _LATEST_JS, _MANAGER_CSS + _LIST_CSS)


def render_filing(acc18):
    return shell("13F filing", "inst", _FILING_BODY, _COMMON_JS + _FILING_JS.replace("__ACC__", acc18), _MANAGER_CSS)


# ------------------------------------------------------------------ insider trading overview
_INS_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Insider trading</h1>
 <p class="mut">Open-market purchases and sales reported by company insiders on SEC Form 4. Grants, option exercises and gifts are left out.</p>
 <div class="card bar"><span id="st" class="mut">Loading…</span><span><button class="btn" id="upd">Update from SEC</button></span></div>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <div class="tabs" id="tabs"></div>
 <div id="view"></div>
 <p class="note" id="note"></p>
 <section class="card" style="margin-top:1rem"><h3>Latest filings (live from EDGAR)</h3><div id="live" class="mut">Loading…</div></section>
</div>
"""

_INS_JS = r"""
let D=null,tab='buys',days=30,plans=true,sym='';
const side=(s)=>s==='buy'?'up':'dn';
function table(cols,rows){const t=el('table',null,'t'),h=el('tr');cols.forEach(c=>{const th=el('th',c.l);if(c.n)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);
 const tb=el('tbody');for(const r of rows){const tr=el('tr');for(const c of cols){const td=c.r?c.r(r):el('td',c.f(r));if(c.n)td.classList.add('n');tr.append(td)}tb.append(tr)}
 if(!rows.length){const tr=el('tr'),td=el('td','No trades in this window','mut');td.colSpan=cols.length;tr.append(td);tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
const tick=r=>{const d=el('td');d.append(el('b',r.symbol));return d};
function viewFor(){const base=[{l:'Ticker',r:tick},{l:'Company',f:r=>r.issuer}];
 if(sym)return D.sym?table([{l:'Date',f:r=>fdate(r.date)},{l:'Insider',f:r=>r.owner},{l:'Role',f:r=>r.role},
  {l:'Side',r:r=>el('td',r.side.toUpperCase()+(r.plan?' (10b5-1)':''),side(r.side))},{l:'Shares',n:1,f:r=>Math.round(r.shares).toLocaleString()},
  {l:'Price',n:1,f:r=>'$'+r.price.toFixed(2)},{l:'Value',n:1,f:r=>money(r.value)}],D.sym.trades):el('div','Loading…','mut');
 if(tab==='clusters')return table(base.concat([{l:'Insiders',n:1,f:r=>String(r.insiders)},{l:'Buys',n:1,f:r=>String(r.trades)},{l:'Total value',n:1,f:r=>money(r.value)},
  {l:'Last buy',f:r=>fdate(r.last)},{l:'Who',f:r=>r.names.slice(0,3).join(', ')+(r.names.length>3?'…':'')}]),D.o.clusters);
 const cols=base.concat([{l:'Insider',f:r=>r.owner},{l:'Role',f:r=>r.role},{l:'Shares',n:1,f:r=>Math.round(r.shares).toLocaleString()},
  {l:'Avg price',n:1,f:r=>'$'+r.price.toFixed(2)},{l:'Value',n:1,r:r=>{const d=el('td',money(r.value),tab==='buys'?'up':'dn');return d}},{l:'Last',f:r=>fdate(r.last)}]);
 return table(cols,tab==='buys'?D.o.top_buys:D.o.top_sells)}
function draw(){if(!D)return;const o=D.o;
 $('stats').replaceChildren(stat('Bought',money(o.buy_value),'open market, last '+o.days+' days'),stat('Sold',money(o.sell_value),plans?'incl. 10b5-1 plans':'excl. 10b5-1 plans'),
  stat('Trades',o.trades.toLocaleString(),'through '+fdate(o.as_of)),stat('Data',o.quarter,'SEC insider data set'));
 const t=$('tabs');t.replaceChildren();
 if(sym){const b=el('button','← all companies','btn');b.onclick=()=>{sym='';$('sq').value='';draw()};t.append(b,el('b','  '+sym+' · '+(D.sym?D.sym.quarter:''),'mut'))}
 else for(const [k,l] of [['buys','Top buys'],['sells','Top sells'],['clusters','Cluster buys']]){const b=el('button',l,'btn'+(k===tab?' on':''));b.onclick=()=>{tab=k;draw()};t.append(b)}
 const sel=el('select',null,'sel');for(const d of [7,30,90]){const op=el('option','Last '+d+' days');op.value=d;op.selected=d===days;sel.append(op)}
 sel.onchange=()=>{days=+sel.value;load()};
 const lab=el('label',null,'mut'),cb=el('input');cb.type='checkbox';cb.checked=!plans;cb.onchange=()=>{plans=!cb.checked;load()};lab.append(cb,document.createTextNode(' Hide 10b5-1 plan sales'));
 const q=el('input',null,'q');q.id='sq';q.placeholder='Ticker';q.value=sym;q.style.minWidth='110px';
 q.onkeydown=e=>{if(e.key==='Enter'){const v=q.value.trim().toUpperCase();if(/^[A-Z][A-Z0-9.\-]{0,9}$/.test(v)){sym=v;D.sym=null;draw();api('/api/insider-trades/'+v).then(r=>{D.sym=r;draw()}).catch(e=>$('msg').textContent=e.message)}else if(!v){sym='';draw()}}};
 t.append(sel,lab,q);
 $('view').replaceChildren(viewFor());
 $('note').textContent='Cluster buy = three or more different insiders buying the same company. Values are shares x reported price. Form 4 data sets are quarterly: the window ends at the last filing in the set.'}
async function load(){try{D={o:await api('/api/insider-trades?days='+days+'&plans='+(plans?1:0)),sym:null};$('msg').textContent='';draw()}catch(e){D=null;$('stats').replaceChildren();$('tabs').replaceChildren();$('view').replaceChildren();$('msg').textContent=e.message}}
async function status(){try{const s=await api('/api/insider-trades/status');$('st').textContent=s.state==='running'?'Updating from SEC… this can take a minute':(s.quarter?'Data: '+s.quarter+' · built '+s.built_at.replace('T',' ').replace('+00:00',' UTC'):'Not built yet')+(s.state==='error'?' · last update failed: '+s.message:'');$('upd').disabled=s.state==='running';return s.state}catch(e){return 'idle'}}
async function poll(){const s=await status();if(s==='running')setTimeout(poll,3000);else load()}
$('upd').onclick=async()=>{try{await api('/api/insider-trades/refresh',{force:false});poll()}catch(e){$('msg').textContent=e.message}};
async function live(){const b=$('live');try{const r=await api('/api/insiders');
 if(!r.length){b.textContent='No recent open-market trades in the latest filings';return}
 b.replaceChildren(table([{l:'Ticker',r:tick},{l:'Insider',f:r=>r.owner},{l:'Role',f:r=>r.role},{l:'Date',f:r=>fdate(r.date)},{l:'Side',r:r=>el('td',r.side.toUpperCase(),side(r.side))},
  {l:'Shares',n:1,f:r=>Math.round(r.shares).toLocaleString()},{l:'Value',n:1,f:r=>money(r.value)}],r.slice(0,15)))}catch(e){b.textContent=e.message}}
load();poll();live();
"""


def render_insiders():
    return shell("Insider trading", "insider", _INS_BODY, _COMMON_JS + _INS_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)


# ------------------------------------------------------------------ dark pool (FINRA ATS weekly)
_DARK_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Dark pool</h1>
 <p class="mut">Trading done on alternative trading systems (ATS, often called dark pools) instead of public exchanges.
 Source: FINRA OTC Transparency, <b>weekly</b> totals per stock and per venue, published about three weeks late. It is aggregate volume, not individual prints.</p>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <div class="grid" style="margin-top:1rem">
  <div class="col">
   <section class="card"><div class="head"><h3>Most traded stocks on ATS venues</h3><span class="head"><input class="q" id="sq" placeholder="Ticker, Enter" style="min-width:120px"></span></div>
    <div id="sym"></div><div class="tbl"><table class="t"><thead><tr><th>#</th><th>Ticker</th><th>Company</th><th class="n">Shares</th><th class="n">Trades</th><th class="n">Avg trade</th><th class="n">vs prior week</th></tr></thead><tbody id="rows"><tr><td class="mut" colspan="7">Loading…</td></tr></tbody></table></div></section>
  </div>
  <div class="col">
   <section class="card"><h3>ATS volume by week</h3><div id="hist"></div></section>
   <section class="card"><h3>Largest ATS venues</h3><div id="venues"></div></section>
  </div>
 </div>
 <p class="note" id="note"></p>
</div>
"""

_DARK_JS = r"""
const num=v=>v>=1e9?(v/1e9).toFixed(2)+'B':v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(1)+'K':String(Math.round(v));
const pctc=v=>v==null?'-':(v>0?'+':'')+v.toFixed(1)+'%';
const cc=v=>v>0?'up':v<0?'dn':'mut';
function bars(h){const W=320,H=120,m=Math.max(...h.map(x=>x.shares))||1,ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox','0 0 '+W+' '+(H+18));svg.setAttribute('width','100%');const bw=W/h.length;
 h.forEach((x,i)=>{const r=document.createElementNS(ns,'rect'),hh=x.shares/m*H;r.setAttribute('x',i*bw+2);r.setAttribute('y',H-hh);r.setAttribute('width',Math.max(1,bw-4));
  r.setAttribute('height',hh);r.setAttribute('fill',i===h.length-1?'#1677ff':'#2b4f86');svg.append(r);
  if(i%3===0||i===h.length-1){const t=document.createElementNS(ns,'text');t.setAttribute('x',i*bw+bw/2);t.setAttribute('y',H+13);t.setAttribute('text-anchor','middle');t.textContent=x.week.slice(5);svg.append(t)}});
 return svg}
async function showSym(v){const b=$('sym');b.replaceChildren(el('span','Loading '+v+'…','mut'));
 try{const d=await api('/api/dark-pool/'+encodeURIComponent(v));b.replaceChildren();
  const c=el('div',null,'card');c.style.margin='.4rem 0 1rem';c.append(el('b',d.symbol+' · week of '+fdate(d.week)));
  if(!d.venues.length)c.append(el('div','No ATS volume reported for this ticker that week','mut'));
  for(const x of d.venues.slice(0,12)){const r=el('div',null,'alloc-row');r.append(el('span',x.name,'nm'),el('span',num(x.shares)+' sh','w'),el('span',x.share_pct.toFixed(1)+'%','w'));c.append(r)}
  b.append(c)}catch(e){b.replaceChildren(el('span',e.message,'err'))}}
$('sq').onkeydown=e=>{if(e.key==='Enter'){const v=e.target.value.trim().toUpperCase();if(/^[A-Z][A-Z0-9.\-]{0,9}$/.test(v))showSym(v)}};
(async()=>{try{const d=await api('/api/dark-pool?top=50');
 $('stats').replaceChildren(stat('Week of',fdate(d.week),'latest published by FINRA'),stat('ATS shares',d.total_shares==null?'-':num(d.total_shares),pctc(d.total_change_pct)+' vs prior week'),
  stat('ATS trades',d.total_trades==null?'-':num(d.total_trades),'all venues'),stat('Venues',String(d.venues.length)+'+','reporting that week'));
 const tb=$('rows');tb.replaceChildren();
 d.top.forEach((r,i)=>{const tr=el('tr'),t=el('td'),a=el('a',r.symbol);a.href='#';a.onclick=e=>{e.preventDefault();$('sq').value=r.symbol;showSym(r.symbol)};t.append(a);
  const ch=el('td',pctc(r.change_pct),'n '+cc(r.change_pct));
  tr.append(el('td',String(i+1)),t,el('td',r.name),el('td',num(r.shares),'n'),el('td',num(r.trades),'n'),el('td',r.avg_trade==null?'-':Math.round(r.avg_trade).toLocaleString()+' sh','n'),ch);tb.append(tr)});
 $('hist').replaceChildren(bars(d.history),el('div','Weekly shares traded on ATS venues, last '+d.history.length+' weeks','note'));
 const vb=$('venues');vb.replaceChildren();for(const v of d.venues){const r=el('div',null,'alloc-row');r.append(el('span',v.name,'nm'),el('span',num(v.shares),'w'),el('span',v.share_pct.toFixed(1)+'%','w'));vb.append(r)}
 $('note').textContent=d.tier_note+' Share counts are as reported by each ATS; FINRA may revise earlier weeks.'}
 catch(e){$('rows').replaceChildren();$('msg').textContent=e.message}})();
"""


def render_dark_pool():
    return shell("Dark pool", "dark", _DARK_BODY, _COMMON_JS + _DARK_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)


# ------------------------------------------------------------------ political trades (US House)
_POL_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Political trades</h1>
 <p class="mut">Stock trades disclosed by members of the US House of Representatives under the STOCK Act (Periodic Transaction Reports).
 Amounts are ranges, so values are estimates (midpoint). Reports arrive up to 45 days after a trade. The Senate is not covered.</p>
 <div class="card bar"><span id="st" class="mut">Loading…</span><span><button class="btn" id="upd">Update from the House Clerk</button></span></div>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <div class="tabs" id="tabs"></div>
 <div id="view"></div>
 <p class="note" id="note"></p>
</div>
"""

_POL_JS = r"""
let D=null,tab='latest',days=90,side='',tk='',mb='';
const range=r=>r.amount_high?money(r.amount_low)+' – '+money(r.amount_high):'Over '+money(r.amount_low);
const kindc=t=>t==='purchase'?'up':t==='exchange'?'mut':'dn';
function table(cols,rows){const t=el('table',null,'t'),h=el('tr');cols.forEach(c=>{const th=el('th',c.l);if(c.n)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);
 const tb=el('tbody');for(const r of rows){const tr=el('tr');for(const c of cols){const td=c.r?c.r(r):el('td',c.f(r));if(c.n)td.classList.add('n');tr.append(td)}tr.append&&tb.append(tr)}
 if(!rows.length){const tr=el('tr'),td=el('td','No trades match','mut');td.colSpan=cols.length;tr.append(td);tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
function viewFor(){
 if(tab==='latest')return table([{l:'Traded',f:r=>fdate(r.date)},{l:'Member',f:r=>r.member+' ('+r.state_dst+')'},
  {l:'Asset',r:r=>{const d=el('td');if(r.ticker)d.append(el('b',r.ticker+' '));d.append(document.createTextNode(r.asset));return d}},
  {l:'Type',r:r=>el('td',r.type+(r.owner?' ('+r.owner+')':''),kindc(r.type))},{l:'Amount',n:1,f:range},{l:'Reported',f:r=>fdate(r.filed)}],D.latest);
 if(tab==='members')return table([{l:'Member',f:r=>r.member},{l:'District',f:r=>r.state_dst},{l:'Trades',n:1,f:r=>String(r.trades)},{l:'Est. volume',n:1,f:r=>money(r.value)}],D.members);
 const rows=tab==='bought'?D.top_bought:D.top_sold;
 return table([{l:'Ticker',r:r=>{const d=el('td');d.append(el('b',r.ticker));return d}},{l:'Asset',f:r=>r.asset},{l:'Members',n:1,f:r=>String(r.members)},
  {l:'Trades',n:1,f:r=>String(r.trades)},{l:'Est. value',n:1,r:r=>el('td',money(r.value),tab==='bought'?'up':'dn')}],rows)}
function draw(){if(!D)return;
 $('stats').replaceChildren(stat('Reports',String(D.reports),'last '+D.days+' days'),stat('Trades',String(D.trades),'disclosed'),stat('Latest report',fdate(D.as_of),'House Clerk'),stat('Source','House','Periodic Transaction Reports'));
 const t=$('tabs');t.replaceChildren();
 for(const [k,l] of [['latest','Latest trades'],['bought','Most bought'],['sold','Most sold'],['members','Most active members']]){const b=el('button',l,'btn'+(k===tab?' on':''));b.onclick=()=>{tab=k;draw()};t.append(b)}
 const sel=el('select',null,'sel');for(const d of [30,90,180,365]){const o=el('option','Last '+d+' days');o.value=d;o.selected=d===days;sel.append(o)}sel.onchange=()=>{days=+sel.value;load()};
 const sd=el('select',null,'sel');for(const [k,l] of [['','All trades'],['buy','Purchases'],['sell','Sales']]){const o=el('option',l);o.value=k;o.selected=k===side;sd.append(o)}sd.onchange=()=>{side=sd.value;load()};
 const q1=el('input',null,'q');q1.placeholder='Ticker';q1.value=tk;q1.style.minWidth='90px';q1.onkeydown=e=>{if(e.key==='Enter'){tk=q1.value.trim().toUpperCase();load()}};
 const q2=el('input',null,'q');q2.placeholder='Member';q2.value=mb;q2.style.minWidth='130px';q2.onkeydown=e=>{if(e.key==='Enter'){mb=q2.value.trim();load()}};
 t.append(sel,sd,q1,q2);$('view').replaceChildren(viewFor());
 $('note').textContent=(D.suspect?D.suspect+' trade(s) dated after their own report were left out as likely typos. ':'')+'Value = midpoint of the disclosed range ("Over $X" counts as $X). SP = spouse, JT = joint, DC = dependent child. Data: disclosures-clerk.house.gov, as of '+fdate(D.as_of)+'.'}
async function load(){try{const p='/api/political-trades?days='+days+(side?'&side='+side:'')+(tk?'&ticker='+encodeURIComponent(tk):'')+(mb?'&member='+encodeURIComponent(mb):'')+'&limit=150';
 D=await api(p);$('msg').textContent='';draw()}catch(e){D=null;$('stats').replaceChildren();$('tabs').replaceChildren();$('view').replaceChildren();$('msg').textContent=e.message}}
async function status(){try{const s=await api('/api/political-trades/status');
 $('st').textContent=s.state==='running'?'Reading House disclosure reports… the first run can take a few minutes':(s.built_at?'Data through '+fdate(s.as_of)+' · '+s.reports+' reports'+(s.failed?' · '+s.failed+' unreadable':''):'Not built yet')+(s.state==='error'?' · last update failed: '+s.message:'');
 $('upd').disabled=s.state==='running';return s.state}catch(e){return 'idle'}}
async function poll(){const s=await status();if(s==='running')setTimeout(poll,3000);else load()}
$('upd').onclick=async()=>{try{await api('/api/political-trades/refresh',{force:false});poll()}catch(e){$('msg').textContent=e.message}};
load();poll();
"""


def render_political():
    return shell("Political trades", "political", _POL_BODY, _COMMON_JS + _POL_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)


# ------------------------------------------------------- investors holding one stock
_INV_CSS = r"""
.sb{display:flex;gap:.5rem;margin:.6rem 0 1rem;flex-wrap:wrap}
.tk{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.45rem .7rem;font:inherit;width:160px;text-transform:uppercase}
.tag{font-size:.6rem;font-weight:700;letter-spacing:.05em;border-radius:5px;padding:.05rem .35rem;margin-left:.4rem;background:#0f2a52;color:#5aa2ff}
.tag.pb{background:#3a2a0c;color:#ffb347}
.ct{font-size:.65rem;font-weight:700;letter-spacing:.05em;border-radius:5px;padding:.1rem .4rem}
.ct.NEW{background:#0c3b2c;color:#22c58b}.ct.INCREASED{background:#10305c;color:#5aa2ff}
.ct.DECREASED{background:#4a3410;color:#ffb347}.ct.UNCHANGED,.ct.OPTIONS{background:#12233d;color:#8497b5}
th.s{cursor:pointer;user-select:none}th.s:hover{color:var(--fg)}
.note{color:var(--mut);font-size:.78rem;margin-top:.7rem}
"""

_INV_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/institutional-investor">Institutional</a> &nbsp;›&nbsp; <b>__TICKER__ investors</b></div>
 <h1 class="title" style="font-size:2rem">__TICKER__ institutional investors</h1>
 <p class="mut" id="sub">Who holds this stock, from Form 13F filings.</p>
 <form id="f" class="sb"><input id="tk" class="tk" placeholder="Ticker" maxlength="10" aria-label="Ticker">
  <button class="btn on" type="submit">Open</button><span id="e" class="err"></span></form>
 <div class="stats" id="stats"></div>
 <section class="card"><div class="head"><h3>Investors <span class="chip" id="cnt"></span></h3></div>
  <div class="tbl"><table class="t"><thead><tr id="hd"></tr></thead><tbody id="rows"></tbody></table></div>
  <div class="pager"><span id="pg"></span><span><button class="btn" id="prev">‹</button> <button class="btn" id="next">›</button></span></div>
  <p class="note" id="note"></p></section>
</div>
"""

_INV_JS = r"""
const TICKER="__TICKER__",LIMIT=20,$=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const money=v=>{if(v==null)return '-';const a=Math.abs(v),s=a>=1e12?'$'+(a/1e12).toFixed(2)+'T':a>=1e9?'$'+(a/1e9).toFixed(2)+'B':a>=1e6?'$'+(a/1e6).toFixed(2)+'M':'$'+Math.round(a).toLocaleString();return (v<0?'-':'')+s};
const num=v=>v==null?'-':Math.round(v).toLocaleString();
const sgn=v=>(v>0?'+':'')+num(v);
const cls=v=>v>0?'up':v<0?'dn':'mut';
const fdate=d=>d?new Date(d+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'-';
async function api(p){const r=await fetch(p),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
let page=1,sortBy='value',sortOrder='desc',totalPages=1;
const COLS=[{k:'name',l:'Investor'},{k:'shares',l:'Shares',n:1},{k:'value',l:'Value',n:1},{k:'ownershipPct',l:'Owns',n:1},
 {k:'prevShares',l:'Prev. shares',n:1},{k:'shareChange',l:'Change',n:1},{k:'shareChangePct',l:'Change %',n:1},
 {k:'changeType',l:'Move',sort:false},{k:'optionsValue',l:'Options (net)',n:1},{k:'filed',l:'Filed'}];
function head(){const hr=$('hd');hr.replaceChildren();
 for(const c of COLS){const th=el('th',c.l+(c.k===sortBy?(sortOrder==='desc'?' ▾':' ▴'):''),(c.n?'n ':'')+(c.sort===false?'':'s'));
  if(c.sort!==false)th.onclick=()=>{sortOrder=sortBy===c.k&&sortOrder==='desc'?'asc':'desc';if(sortBy!==c.k&&c.k==='name')sortOrder='asc';sortBy=c.k;page=1;load()};hr.append(th)}}
function stat(k,v,d){const c=el('div',null,'card stat');c.append(el('div',k,'k'),el('div',v,'v'),el('div',d||'','d mut'));return c}
function drawSummary(d){const s=d.summary;
 $('sub').textContent=d.coverage.quarter+' filings: '+s.filerCount+' institutions hold '+TICKER+' (vs previous quarter: '+s.newCount+' new, '+s.increasedCount+' added, '+s.decreasedCount+' reduced, '+s.soldOutCount+' sold out).';
 $('stats').replaceChildren(
  stat('Institutions',num(s.filerCount),s.topFundCount+' top-100 funds · '+s.primeBrokerCount+' banks/prime brokers'),
  stat('Shares held',num(s.stockShares),s.heldPct==null?'share count unavailable':s.heldPct+'% of '+num(s.sharesOutstanding)+' outstanding'),
  stat('Value held',money(s.stockValue),'stock only'),
  stat('Options (net)',money(s.optionsValue),'calls '+money(s.callValue)+' · puts '+money(s.putValue)+' · '+s.filersWithOptions+' filers'));
 $('cnt').textContent=String(s.filerCount)}
function draw(d){head();const tb=$('rows');tb.replaceChildren();
 for(const r of d.data){const tr=el('tr'),n=el('td');
  if(/^[0-9]{1,10}$/.test(r.cik)){const a=el('a',r.name);a.href='/institutional-investor/manager/'+r.cik;n.append(a)}else n.textContent=r.name;
  if(r.isTopFund)n.append(el('span','TOP FUND','tag'));if(r.isPrimeBroker)n.append(el('span','BANK','tag pb'));
  const mv=el('td'),ct=['NEW','INCREASED','DECREASED','UNCHANGED','OPTIONS'].includes(r.changeType)?r.changeType:'UNCHANGED';mv.append(el('span',ct,'ct '+ct));
  const cells=[n,el('td',num(r.shares),'n'),el('td',money(r.value),'n'),el('td',r.ownershipPct==null?'-':r.ownershipPct.toFixed(2)+'%','n'),
   el('td',num(r.prevShares),'n'),el('td',sgn(r.shareChange),'n '+cls(r.shareChange)),
   el('td',r.shareChangePct==null?'-':(r.shareChangePct>0?'+':'')+r.shareChangePct.toFixed(1)+'%','n '+cls(r.shareChangePct)),mv,
   el('td',r.optionPositions?money(r.optionsValue):'-','n'),el('td',fdate(r.filed))];
  tr.append(...cells);tb.append(tr)}
 const p=d.pagination;totalPages=p.totalPages;
 $('pg').textContent=p.total?((p.page-1)*p.limit+1)+' – '+Math.min(p.page*p.limit,p.total)+' of '+p.total:'No investors';
 $('prev').disabled=p.page<=1;$('next').disabled=p.page>=p.totalPages;
 $('note').textContent='Source: SEC Form 13F ('+d.coverage.quarter+'). Filed up to 45 days after quarter end, long positions only; options value is calls minus puts at reported underlying value. Ownership uses the latest share count reported to SEC.'}
async function load(){$('e').textContent='';
 try{const d=await api('/api/investors/'+encodeURIComponent(TICKER)+'?page='+page+'&limit='+LIMIT+'&sortBy='+sortBy+'&sortOrder='+sortOrder);
  document.title=TICKER+' institutional investors';drawSummary(d);draw(d)}
 catch(e){head();$('e').textContent=e.message}}
$('prev').onclick=()=>{if(page>1){page--;load()}};$('next').onclick=()=>{if(page<totalPages){page++;load()}};
$('f').onsubmit=e=>{e.preventDefault();const v=$('tk').value.trim().toUpperCase();
 if(!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(v)){$('e').textContent='Enter a ticker, e.g. AAPL';return}
 location.href='/stock/'+encodeURIComponent(v)+'/investors'};
head();load();
"""


def render_investors(ticker):
    import re
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker):
        raise ValueError("bad ticker")
    return shell(f"{ticker} institutional investors", "inst", _INV_BODY.replace("__TICKER__", ticker),
                 _INV_JS.replace("__TICKER__", ticker), _MANAGER_CSS + _LIST_CSS + _INV_CSS)
