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

NAV_ITEMS = (("dash", "/", "Dashboard"), ("inst", "/institutional-investor", "Smart Money"))


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
api('/api/manager/'+CIK).then(drawHeader).catch(e=>{$('name').textContent='Manager not available';$('msg').textContent=e.message});
show(0);
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
 <section class="card"><h3>Examples</h3>__EXAMPLES__</section>
</div>
"""

_INST_JS = r"""
document.getElementById('f').onsubmit=e=>{e.preventDefault();
 const v=document.getElementById('cik').value.trim().replace(/^0+/,'');
 if(!/^[0-9]{1,10}$/.test(v)){document.getElementById('e').textContent='CIK must be 1-10 digits';return}
 location.href='/institutional-investor/manager/'+v.padStart(10,'0')};
"""


def render_institutional():
    items = "".join(f'<div style="padding:.45rem 0;border-top:1px solid var(--line)">'
                    f'<a href="/institutional-investor/manager/{c}-{slug}">{name}</a> '
                    f'<span class="mut">CIK {c}</span></div>' for c, slug, name in EXAMPLES)
    return shell("Institutional investors", "inst", _INST_BODY.replace("__EXAMPLES__", items), _INST_JS)
