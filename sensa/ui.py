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

NAV_ITEMS = (("dash", "/", "Dashboard"), ("picks", "/picks", "Picks"), ("brief", "/brief", "Brief"), ("mine", "/my-portfolio", "My portfolio"), ("smart", "/smart-money", "Smart Money"),
             ("inst", "/institutional-investor", "Funds"), ("insider", "/inside-trade", "Insiders"), ("dark", "/dark-pool", "Dark pool"), ("political", "/political-trades", "Politicians"),
             ("alerts", "/smart-money/alerts", "Alerts"), ("lab", "/portfolio-lab", "Lab"), ("value", "/valuation", "Value"), ("health", "/health", "Status"))


LINK_JS = r"""
function tkLink(sym,cls){const a=document.createElement('a');a.textContent=sym;
 if(/^[A-Z][A-Z0-9.\-]{0,9}$/.test(sym)){a.href='/stock/'+encodeURIComponent(sym);a.className=(cls||'')+' tk-link'}return a}
(function(){const f=document.getElementById('gs');if(!f)return;
 f.onsubmit=e=>{e.preventDefault();const v=document.getElementById('gsq').value.trim().toUpperCase();
  if(/^[A-Z][A-Z0-9.\-]{0,9}$/.test(v))location.href='/stock/'+encodeURIComponent(v)}})();
"""

PERF_JS = r"""
const fmtPct=v=>v==null?'-':(v>0?'+':'')+v.toFixed(1)+'%',pcls=v=>v==null?'mut':v>0?'up':v<0?'dn':'mut';
function perfView(kind,render){const box=document.createElement('div');
 const line=(t,c)=>{const d=document.createElement('div');d.textContent=t;if(c)d.className=c;return d};
 async function load(){let j;
  try{const r=await fetch('/api/performance/'+kind);j=await r.json();if(!r.ok)throw new Error(j.error||r.status)}
  catch(e){box.replaceChildren(line(e.message,'err'));return}
  const running=j.status&&j.status.state==='running';
  if(j.data==null){const b=document.createElement('button');b.className='btn';b.textContent='Compute now';b.disabled=running;
   b.onclick=async()=>{await fetch('/api/performance/'+kind+'/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});load()};
   box.replaceChildren(line(running?'Pricing the positions… this takes a few minutes the first time.':(j.message||'Not computed yet.'),'mut'),
    ...(j.status&&j.status.state==='error'?[line('Last run failed: '+j.status.message,'err')]:[]),b);
   if(running)setTimeout(load,4000);return}
  const note=line('Prices as of the last close (Yahoo Finance), computed '+(j.generated||'').replace('T',' ')+' UTC'+(running?' · refreshing…':'')+
   '. Buy-and-hold on reported positions; "since filing" starts the day the report became public. Not investment advice.','note');
  box.replaceChildren(render(j.data),note);if(running)setTimeout(load,4000)}
 box.textContent='Loading…';load();return box}
"""

NAV_CSS = r"""
.nav .gs{margin-left:auto}.nav .gs input{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.3rem .6rem;font:inherit;width:210px}.nav .gs input:not(:placeholder-shown){text-transform:uppercase}
a.tk-link{font-weight:700}
"""


def nav(active):
    items = "".join(f'<a class="item{" on" if k == active else ""}" href="{h}">{t}</a>'
                    for k, h, t in NAV_ITEMS)
    search = ('<form id="gs" class="gs" autocomplete="off"><input id="gsq" placeholder="Open a stock: AAPL" maxlength="10" '
              'aria-label="Open a stock page"></form>')
    return f'<nav class="nav"><span class="brand">Options<i>Dash</i></span>{items}{search}</nav>'


def shell(title, active, body, script="", extra_css=""):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>{BASE_CSS}{NAV_CSS}{extra_css}</style></head><body>'
            f'{nav(active)}{body}'
            f'<footer class="foot">Research artifact - not investment advice. '
            f'13F data: SEC EDGAR. Tickers: OpenFIGI.</footer>'
            f'<script>{LINK_JS}{PERF_JS}</script><script>{script}</script></body></html>')


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
   <section class="card"><h3>Portfolio at today's prices</h3><div id="perf" class="mut">Pricing the positions… the first time can take half a minute.</div></section>
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
  d.append(tkLink(h.ticker),el('div',money(h.value),'mut'),el('div',h.weight+'% of portfolio','mut'),b);t.append(d)}
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
  const tkc=el('span',null,'tk');tkc.append(tkLink(x.ticker));r.append(sw,tkc,el('span',x.name,'nm'),el('span',x.weight.toFixed(2)+'%','w'));a.append(r)})}
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
api('/api/portfolio/'+CIK).then(p=>{const b=$('perf'),pc=v=>el('span',fmtPct(v),pcls(v));
 if(p.covered_positions===0){b.textContent='No positions could be priced.';return}
 const sum=el('div',null,'meta');for(const [k,v] of [['Value at quarter end',money(p.value_period_end)],['Value now',money(p.value_now)],['Since quarter end',fmtPct(p.return_since_period_pct)],
  ['Since filing ('+fdate(p.filed)+')',fmtPct(p.return_since_filing_pct)],['S&P 500 since filing',fmtPct(p.spy_since_filing_pct)],['Priced',p.covered_pct.toFixed(0)+'% of value']]){const d=el('div'),a=el('span',k),bb=el('b',v);d.append(a,bb);sum.append(d)}
 const t=el('table',null,'t'),h=el('tr');for(const x of ['Stock','Weight','Price at filing','Price now','Since filing']){h.append(el('th',x))}const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
 for(const r of p.rows){const tr=el('tr'),c=el('td');c.append(tkLink(r.ticker));tr.append(c,el('td',r.weight==null?'-':r.weight.toFixed(2)+'%'),el('td','$'+r.px_filed.toFixed(2)),el('td','$'+r.px_now.toFixed(2)),el('td',fmtPct(r.change_since_filing_pct),pcls(r.change_since_filing_pct)));tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);
 b.replaceChildren(sum,w,el('div','Buy-and-hold on the largest reported positions with a listed ticker, priced at the last close ('+(p.as_of||'-')+'). 13F shows long positions at quarter end only; the fund may have traded since.','note'))}).catch(e=>{$('perf').textContent=e.message});
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
    tkLink(ch.ticker),document.createTextNode(' '+money(ch.type==='exited'?ch.value_prev:ch.value_now)+' ('+(ch.shares_now-ch.shares_prev>=0?'+':'')+Math.round(ch.shares_now-ch.shares_prev).toLocaleString()+' sh)'));ul.append(li)}
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
 <div class="tabs" id="views"></div>
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
   d.append(tkLink(s.ticker));return d}},
  {k:'issuer',l:'Company',dir:1,f:s=>s.issuer},
  {k:'holders',l:'Funds',n:1,r:s=>cell(s.holders+' / '+O.cohort)},
  {k:'dh',l:'vs last Q',n:1,v:s=>s.holders-s.holders_prev,r:s=>cell((s.holders-s.holders_prev>0?'+':'')+(s.holders-s.holders_prev),cls(s.holders-s.holders_prev))},
  {k:'value',l:'Value',n:1,f:s=>money(s.value)},
  {k:'avg_weight',l:'Avg weight',n:1,f:s=>s.avg_weight.toFixed(2)+'%'},
  {k:'active_flow',l:'Active flow',n:1,r:s=>cell(smoney(s.active_flow),cls(s.active_flow))},
  {k:'added',l:'Added',n:1,f:s=>String(s.added)},{k:'reduced',l:'Reduced',n:1,f:s=>String(s.reduced)},
  {k:'new',l:'New',n:1,f:s=>String(s.new)},{k:'exited',l:'Exited',n:1,f:s=>String(s.exited)}];
 return table(cols,rows,'holders')}
function perfFundsView(){return perfView('funds',rows=>{const pc=(k)=>f=>cell(fmtPct(f[k]),pcls(f[k]));
 const alpha=f=>f.return_since_filing_pct==null||f.spy_since_filing_pct==null?null:Math.round((f.return_since_filing_pct-f.spy_since_filing_pct)*100)/100;
 const cols=[{k:'rank',l:'#',dir:1,f:f=>String(f.rank)},
  {k:'name',l:'Fund',dir:1,r:f=>{const d=el('td');if(/^[0-9]{1,10}$/.test(f.cik)){const a=el('a',f.name);a.href='/institutional-investor/manager/'+f.cik;d.append(a)}else d.textContent=f.name;return d}},
  {k:'aum',l:'Reported value',n:1,f:f=>money(f.aum)},
  {k:'return_since_period_pct',l:'Since quarter end',n:1,v:f=>f.return_since_period_pct==null?-1e9:f.return_since_period_pct,r:pc('return_since_period_pct')},
  {k:'return_since_filing_pct',l:'Since filing',n:1,v:f=>f.return_since_filing_pct==null?-1e9:f.return_since_filing_pct,r:pc('return_since_filing_pct')},
  {k:'spy_since_filing_pct',l:'S&P 500 since filing',n:1,v:f=>f.spy_since_filing_pct==null?-1e9:f.spy_since_filing_pct,r:pc('spy_since_filing_pct')},
  {k:'alpha',l:'vs S&P 500',n:1,v:f=>alpha(f)==null?-1e9:alpha(f),r:f=>cell(fmtPct(alpha(f)),pcls(alpha(f)))},
  {k:'covered_pct',l:'Priced',n:1,f:f=>f.covered_pct.toFixed(0)+'% of value'}];
 return table(cols,rows,'return_since_filing_pct')})}
function list(title,rows,right,sub){const c=el('section',null,'card');c.append(el('h3',title));if(sub)c.append(el('div',sub,'note'));
 if(!rows.length)c.append(el('div','Nothing to show','mut'));
 for(const s of rows.slice(0,10)){const r=el('div',null,'mrow'),l=el('span'),b=tkLink(s.ticker);l.append(b,document.createTextNode(' '+s.issuer));
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
  {k:'top',l:'Top holdings',sort:false,r:f=>{const d=el('td');for(const t of f.top.slice(0,3)){const c=el('span',null,'chip');c.append(tkLink(t.ticker));d.append(c)}return d}},
  {k:'top10_pct',l:'Top 10',n:1,f:f=>f.top10_pct.toFixed(1)+'%'},
  {k:'turnover_pct',l:'Turnover',n:1,v:f=>f.turnover_pct==null?-1:f.turnover_pct,f:f=>f.turnover_pct==null?'-':f.turnover_pct.toFixed(1)+'%'},
  {k:'new',l:'New',n:1,v:f=>f.new==null?-1:f.new,f:f=>f.new==null?'-':String(f.new)},
  {k:'exited',l:'Exited',n:1,v:f=>f.exited==null?-1:f.exited,f:f=>f.exited==null?'-':String(f.exited)}];
 return table(cols,O.funds,'rank')}
function draw(){if(!O)return;const v=$('view');
 v.replaceChildren(tab==='held'?heldView():tab==='moves'?movesView():tab==='perf'?perfFundsView():fundsView())}
function drawAll(){$('stats').replaceChildren(
  ...[['Funds in view',String(O.cohort),O.comparable+' comparable with '+O.prev_quarter],['Reported value',money(O.total_aum),O.quarter],
      ['Distinct stocks',O.distinct_stocks.toLocaleString(),'held by at least one of them'],['Stock splits adjusted',String((O.splits||[]).length),'so they do not look like buying']]
   .map(([k,v,d])=>{const c=el('div',null,'card stat');c.append(el('div',k,'k'),el('div',v,'v'),el('div',d,'d mut'));return c}));
 const t=$('tabs');t.replaceChildren();
 for(const [k,l] of [['held','Most held'],['moves','Moves'],['funds','Top funds'],['perf','Performance']]){const b=el('button',l,'btn'+(k===tab?' on':''));b.onclick=()=>{tab=k;sortKey=null;drawAll()};t.append(b)}
 const sel=el('select',null,'sel');for(const [k,l] of [['stock','Stocks & ADRs'],['all','Include ETFs & other']]){const o=el('option',l);o.value=k;o.selected=k===kinds;sel.append(o)}
 sel.onchange=()=>{kinds=sel.value;draw()};if(tab==='held'||tab==='moves')t.append(sel);
 $('note').textContent=(O.live?'Live view: only the '+O.live.reported+' of '+O.live.of+' top funds that have already filed '+O.quarter+' are included, each compared with its own previous quarter. It fills up as more funds report. ':'')+'Funds = how many of the '+O.cohort+' filers hold it. Active flow = net shares bought or sold beyond each fund\'s own proportional growth, at quarter-end prices. 13F lists long positions only, reported up to 45 days after quarter end.';
 draw()}
async function status(){try{const s=await api('/api/smart-money/status');
  $('st').textContent=s.state==='running'?'Updating from SEC… this can take a few minutes':(s.quarter?'Data: '+s.quarter+' · built '+s.built_at.replace('T',' ').replace('+00:00',' UTC'):'Not built yet')+(s.state==='error'?' · last update failed: '+s.message:'');
  $('upd').disabled=s.state==='running';return s.state}catch(e){$('st').textContent='';return 'idle'}}
let view='full',liveInfo=null;
function drawViews(){const v=$('views');v.replaceChildren();if(!liveInfo)return;
 for(const [k,l] of [['full','Complete quarter'],['live',liveInfo.quarter+' live: '+liveInfo.live.reported+' of '+liveInfo.live.of+' top funds reported']]){
  const b=el('button',l,'btn'+(k===view?' on':''));b.onclick=()=>{view=k;load()};v.append(b)}}
async function checkLive(){try{liveInfo=await api('/api/smart-money/overview?view=live')}catch(e){liveInfo=null;if(view==='live')view='full'}drawViews()}
async function load(){try{O=await api('/api/smart-money/overview'+(view==='live'?'?view=live':''));$('msg').textContent='';drawAll();drawViews()}catch(e){O=null;$('stats').replaceChildren();$('tabs').replaceChildren();$('view').replaceChildren();$('msg').textContent=e.message}}
async function poll(){const s=await status();if(s==='running')setTimeout(poll,3000);else load()}
$('upd').onclick=async()=>{try{await api('/api/smart-money/refresh',{force:false});poll()}catch(e){$('msg').textContent=e.message}};
checkLive();load();poll();setInterval(checkLive,300000);
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
 for(const h of d.holdings){const tr=el('tr'),t=el('td'),b=tkLink(h.ticker);t.append(b);
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
const tick=r=>{const d=el('td');d.append(tkLink(r.symbol));return d};
const own=r=>{const n=r.owner.split(' / ');return n.slice(0,2).join(' / ')+(n.length>2?' +'+(n.length-2)+' more':'')};
const tick2=r=>{const d=el('td');d.append(tkLink(r.symbol));return d};
function viewFor(){const base=[{l:'Ticker',r:tick},{l:'Company',f:r=>r.issuer}];
 if(tab==='perf'&&!sym)return perfView('insiders',d=>{const p=d.performance,w=el('div');
  const st=el('div',null,'stats');st.append(stat('Buys measured',String(p.n),'open market, $25k or more'),stat('Average return',fmtPct(p.avg_return_pct),'median '+fmtPct(p.median_return_pct)+' · since purchase'),
   stat('S&P 500',fmtPct(p.spy_pct),'over the same days'),stat('Winners',p.win_rate_pct==null?'-':p.win_rate_pct+'%','of purchases'));
  const bw=cols=>rows=>table(cols,rows);const pc=r=>el('td',fmtPct(r.return_pct),'n '+pcls(r.return_pct));
  const cols=[{l:'Ticker',r:tick2},{l:'Insider',f:r=>own(r)},{l:'Role',f:r=>r.role},{l:'Bought',f:r=>fdate(r.date)},{l:'Price',n:1,f:r=>'$'+r.price.toFixed(2)},{l:'Return',n:1,r:pc}];
  const h=[{l:'Ticker',r:tick2},{l:'Insider',f:r=>own(r)},{l:'Role',f:r=>r.role},{l:'Shares held',n:1,f:r=>Math.round(r.shares).toLocaleString()},
   {l:'Value now',n:1,f:r=>money(r.value)},{l:'Own buys',n:1,r:r=>el('td',fmtPct(r.buy_return_pct),'n '+pcls(r.buy_return_pct))}];
  const sec=(t,x)=>{const c=el('section',null,'card');c.style.marginTop='1rem';c.append(el('h3',t),x);return c};
  w.append(st,sec('Best purchases',table(cols,p.best)),sec('Worst purchases',table(cols,p.worst)),sec('Largest insider holdings (reported balance, today\'s price)',table(h,d.holdings)));return w});
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
 else for(const [k,l] of [['buys','Top buys'],['sells','Top sells'],['clusters','Cluster buys'],['perf','Performance']]){const b=el('button',l,'btn'+(k===tab?' on':''));b.onclick=()=>{tab=k;draw()};t.append(b)}
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
 d.top.forEach((r,i)=>{const tr=el('tr'),t=el('td'),a=tkLink(r.symbol);t.append(a);const vb=el('a',' venues');vb.href='#';vb.className='mut';vb.onclick=e=>{e.preventDefault();$('sq').value=r.symbol;showSym(r.symbol)};t.append(vb);
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
const QS=new URLSearchParams(location.search);
let D=null,tab='latest',days=QS.get('member')||QS.get('ticker')?365:90,side='',tk=(QS.get('ticker')||'').toUpperCase().slice(0,10),mb=(QS.get('member')||'').slice(0,60);
const range=r=>r.amount_high?money(r.amount_low)+' – '+money(r.amount_high):'Over '+money(r.amount_low);
const kindc=t=>t==='purchase'?'up':t==='exchange'?'mut':'dn';
function table(cols,rows){const t=el('table',null,'t'),h=el('tr');cols.forEach(c=>{const th=el('th',c.l);if(c.n)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);
 const tb=el('tbody');for(const r of rows){const tr=el('tr');for(const c of cols){const td=c.r?c.r(r):el('td',c.f(r));if(c.n)td.classList.add('n');tr.append(td)}tr.append&&tb.append(tr)}
 if(!rows.length){const tr=el('tr'),td=el('td','No trades match','mut');td.colSpan=cols.length;tr.append(td);tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
function viewFor(){
 if(tab==='perf')return perfView('members',rows=>{const pc=k=>r=>el('td',fmtPct(r[k]),'n '+pcls(r[k]));
  return table([{l:'Member',r:r=>{const d=el('td'),a=el('a',r.member);a.href='/political-trades?member='+encodeURIComponent(r.member);d.append(a);return d}},
   {l:'Priced buys',n:1,f:r=>String(r.buys)},{l:'Est. volume',n:1,f:r=>money(r.est_volume)},{l:'Since trade',n:1,r:pc('return_since_trade_pct')},
   {l:'S&P 500',n:1,r:pc('spy_since_trade_pct')},{l:'Since filing',n:1,r:pc('return_since_filing_pct')},{l:'S&P 500',n:1,r:pc('spy_since_filing_pct')},
   {l:'Best buy',r:r=>{const d=el('td');d.append(tkLink(r.best_trade.ticker),document.createTextNode(' '+fmtPct(r.best_trade.return_pct)));return d}}],rows)});
 if(tab==='latest')return table([{l:'Traded',f:r=>fdate(r.date)},{l:'Member',r:r=>{const d=el('td'),a=el('a',r.member);a.href='/political-trades?member='+encodeURIComponent(r.member);d.append(a,document.createTextNode(' ('+r.state_dst+')'));return d}},
  {l:'Asset',r:r=>{const d=el('td');if(r.ticker){d.append(tkLink(r.ticker),document.createTextNode(' '))}d.append(document.createTextNode(r.asset));return d}},
  {l:'Type',r:r=>el('td',r.type+(r.owner?' ('+r.owner+')':''),kindc(r.type))},{l:'Amount',n:1,f:range},{l:'Reported',f:r=>fdate(r.filed)}],D.latest);
 if(tab==='members')return table([{l:'Member',r:r=>{const d=el('td'),a=el('a',r.member);a.href='/political-trades?member='+encodeURIComponent(r.member);d.append(a);return d}},{l:'District',f:r=>r.state_dst},{l:'Trades',n:1,f:r=>String(r.trades)},{l:'Est. volume',n:1,f:r=>money(r.value)}],D.members);
 const rows=tab==='bought'?D.top_bought:D.top_sold;
 return table([{l:'Ticker',r:r=>{const d=el('td');d.append(tkLink(r.ticker));return d}},{l:'Asset',f:r=>r.asset},{l:'Members',n:1,f:r=>String(r.members)},
  {l:'Trades',n:1,f:r=>String(r.trades)},{l:'Est. value',n:1,r:r=>el('td',money(r.value),tab==='bought'?'up':'dn')}],rows)}
function draw(){if(!D)return;
 $('stats').replaceChildren(stat('Reports',String(D.reports),'last '+D.days+' days'),stat('Trades',String(D.trades),'disclosed'),stat('Latest report',fdate(D.as_of),'House Clerk'),stat('Source','House','Periodic Transaction Reports'));
 const t=$('tabs');t.replaceChildren();
 for(const [k,l] of [['latest','Latest trades'],['bought','Most bought'],['sold','Most sold'],['members','Most active members'],['perf','Performance']]){const b=el('button',l,'btn'+(k===tab?' on':''));b.onclick=()=>{tab=k;draw()};t.append(b)}
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
.tag.pb{background:#3a2a0c;color:#ffb347}.tag.nw{background:#0c3b2c;color:#22c58b}
.ct{font-size:.65rem;font-weight:700;letter-spacing:.05em;border-radius:5px;padding:.1rem .4rem}
.ct.NEW{background:#0c3b2c;color:#22c58b}.ct.INCREASED{background:#10305c;color:#5aa2ff}
.ct.DECREASED{background:#4a3410;color:#ffb347}.ct.UNCHANGED,.ct.OPTIONS{background:#12233d;color:#8497b5}
th.s{cursor:pointer;user-select:none}th.s:hover{color:var(--fg)}
.note{color:var(--mut);font-size:.78rem;margin-top:.7rem}
"""

_INV_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/stock/__TICKER__">__TICKER__</a> &nbsp;›&nbsp; <b>Institutional investors</b></div>
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
 const cv=d.coverage;
 $('sub').textContent=(cv.carriedFrom?cv.currentFilers+' of '+s.filerCount+' institutions have already reported '+cv.quarter+' (read live from EDGAR); the other '+cv.carriedFilers+' are carried from '+cv.carriedFrom+' until their report arrives. ':'')+d.coverage.quarter+' filings: '+s.filerCount+' institutions hold '+TICKER+' (vs previous quarter: '+s.newCount+' new, '+s.increasedCount+' added, '+s.decreasedCount+' reduced, '+s.soldOutCount+' sold out).';
 $('stats').replaceChildren(
  stat('Institutions',num(s.filerCount),s.topFundCount+' top-100 funds · '+s.primeBrokerCount+' banks/prime brokers'),
  stat('Shares held',num(s.stockShares),s.heldPct==null?'share count unavailable':s.heldPct+'% of '+num(s.sharesOutstanding)+' outstanding'),
  stat('Value held',money(s.stockValue),'stock only'),
  stat('Options (net)',money(s.optionsValue),'calls '+money(s.callValue)+' · puts '+money(s.putValue)+' · '+s.filersWithOptions+' filers'));
 $('cnt').textContent=String(s.filerCount)}
function draw(d){head();const tb=$('rows');tb.replaceChildren();
 for(const r of d.data){const tr=el('tr'),n=el('td');
  if(/^[0-9]{1,10}$/.test(r.cik)){const a=el('a',r.name);a.href='/institutional-investor/manager/'+r.cik;n.append(a)}else n.textContent=r.name;
  if(r.isCurrent)n.append(el('span','NEW REPORT','tag nw'));
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
 $('note').textContent='Source: SEC Form 13F ('+d.coverage.quarter+(d.coverage.carriedFrom?', plus '+d.coverage.carriedFrom+' for filers that have not reported yet':'')+'). Filed up to 45 days after quarter end, long positions only; options value is calls minus puts at reported underlying value. Ownership uses the latest share count reported to SEC.'}
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


# ------------------------------------------------------------------ one stock: everything about a ticker
_STOCK_CSS = r"""
.hd{display:flex;gap:1.2rem;align-items:flex-end;flex-wrap:wrap;margin:.2rem 0 .6rem}
.px{font-size:2.2rem;font-weight:800}.chg{font-size:1.05rem;font-weight:600}
.jump{display:flex;gap:.4rem;flex-wrap:wrap;margin:.4rem 0 1rem}.jump a{padding:.25rem .65rem;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--fg)}
.kv{display:grid;grid-template-columns:1fr auto;gap:.15rem .8rem}.kv span:nth-child(odd){color:var(--mut)}.kv span:nth-child(even){text-align:right;font-variant-numeric:tabular-nums}
.news a{color:var(--fg)}.news li{margin:.5rem 0;list-style:none}.news ul{padding:0;margin:0}
.tf{background:var(--card2);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:.15rem .6rem;margin-right:4px;cursor:pointer}.tf.on{border-color:var(--acc);color:var(--acc)}
.chartbar{position:relative;display:flex;gap:.3rem;align-items:center;flex-wrap:wrap}
.indmenu{position:absolute;right:0;top:2rem;z-index:20;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.6rem .8rem;min-width:260px;box-shadow:0 8px 24px #0008}
.indmenu[hidden]{display:none}.indrow{display:flex;gap:.5rem;align-items:center;padding:.12rem 0;cursor:pointer;font-size:.85rem}
.sm{font-size:.82rem}.sm td,.sm th{padding:.3rem .4rem}
.grid{grid-template-columns:minmax(0,1.5fr) minmax(380px,1fr)}@media(max-width:1000px){.grid{grid-template-columns:1fr}}
"""

_STOCK_BODY = r"""
<div class="wrap">
 <div class="crumb"><a href="/">Dashboard</a> &nbsp;›&nbsp; <b>__T__</b></div>
 <div class="hd"><div><h1 class="title" style="font-size:2.2rem;margin:0">__T__</h1><div class="mut" id="co">Loading…</div></div>
  <div><span class="px" id="px">-</span> <span class="chg" id="chg"></span><div class="mut sm" id="asof"></div></div></div>
 <div class="jump"><a href="#chartc">Chart</a><a href="#optc">Options</a><a href="#newsc">News</a><a href="#instc">Institutions</a>
  <a href="#insc">Insiders</a><a href="#darkc">Dark pool</a><a href="#polc">Politicians</a><a href="/stock/__T__/investors">All investors →</a></div>
 <div id="msg" class="err"></div>
 <div class="stats" id="stats"></div>
 <div class="grid">
  <div class="col">
   <section class="card" id="chartc"><div class="head"><h3>Chart</h3><div class="chartbar"><div id="tfs"></div><button class="tf" id="indbtn" type="button">Indicators ▾</button><div id="indmenu" class="indmenu" hidden></div></div></div><div id="chart" style="height:380px"></div><div id="subcharts"></div><div id="chartmsg"></div></section>
   <section class="card news" id="newsc"><h3>News</h3><div id="news" class="mut">Loading…</div></section>
   <section class="card" id="insc"><h3>Insider trades</h3><div id="ins" class="mut">Loading…</div></section>
   <section class="card" id="polc"><h3>Politicians (US House)</h3><div id="pol" class="mut">Loading…</div></section>
  </div>
  <div class="col">
   <section class="card" id="optc"><h3>Options overview</h3><div id="opts" class="mut">Loading…</div></section>
   <section class="card" id="thermc"><h3>Valuation thermometer</h3><div id="therm" class="mut">Loading…</div></section>
   <section class="card" id="fundc"><h3>Valuation and quality</h3><div id="fund" class="mut">Loading…</div></section>
   <section class="card" id="flowc"><h3>Options flow</h3><div id="flow" class="mut">Loading…</div></section>
   <section class="card"><h3>Analyst consensus</h3><div id="analyst" class="mut">Loading…</div></section>
   <section class="card" id="instc"><h3>Top institutional holders</h3><div id="inst" class="mut">Matching the ticker to its 13F security… the first visit to a stock can take up to a minute.</div></section>
   <section class="card" id="darkc"><h3>Dark pool (ATS)</h3><div id="dark" class="mut">Loading…</div></section>
   <section class="card"><h3>Short volume (FINRA)</h3><div id="shv" class="mut">Loading…</div></section>
  </div>
 </div>
</div>
<script src="/static/lightweight-charts.js"></script>
"""

_STOCK_JS = r"""
const T="__T__";
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const $=id=>document.getElementById(id);
const money=v=>{if(v==null)return '-';const a=Math.abs(v),s=a>=1e12?'$'+(a/1e12).toFixed(2)+'T':a>=1e9?'$'+(a/1e9).toFixed(2)+'B':a>=1e6?'$'+(a/1e6).toFixed(2)+'M':'$'+Math.round(a).toLocaleString();return (v<0?'-':'')+s};
const num=v=>v==null?'-':Math.round(v).toLocaleString();
const px=v=>v==null?'-':v.toFixed(2);
const fdate=d=>d?new Date(d+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'-';
const cls=v=>v>0?'up':v<0?'dn':'mut';
const safeUrl=u=>/^https?:\/\//i.test(u)?u:null;
async function api(p){const r=await fetch(p),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
const fail=(b,e)=>b.replaceChildren(el('div',String(e.message||e),'err'));
const none=(b,t)=>b.replaceChildren(el('div',t,'mut'));
function kv(rows){const d=el('div',null,'kv');for(const [k,v,c] of rows){d.append(el('span',k),el('span',v,c))}return d}
function link(text,href,cls){const a=el('a',text,cls);a.href=href;return a}
function table(head,rows,numCols){const t=el('table',null,'t sm'),h=el('tr');head.forEach((x,i)=>{const th=el('th',x);if(numCols.includes(i))th.className='n';h.append(th)});
 const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
 for(const r of rows){const tr=el('tr');r.forEach((c,i)=>{const td=c instanceof Node?(()=>{const d=el('td');d.append(c);return d})():el('td',c);if(numCols.includes(i))td.classList.add('n');tr.append(td)});tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
let Q=null,C=null;
function drawQuote(){if(!Q)return;
 $('px').textContent='$'+px(Q.price);const ch=Q.change_pct;
 $('chg').textContent=(Q.change==null?'':(Q.change>0?'+':'')+Q.change.toFixed(2)+' ')+(ch==null?'':'('+(ch>0?'+':'')+ch.toFixed(2)+'%)');$('chg').className='chg '+cls(ch);
 $('asof').textContent=Q.last_trade_time?'Delayed quote · last trade '+Q.last_trade_time.replace('T',' '):'Delayed quote';
 const cap=C&&C.shares_outstanding&&Q.price?C.shares_outstanding*Q.price:null;
 $('stats').replaceChildren(
  (()=>{const c=stat('Day range',px(Q.low)+' – '+px(Q.high),'open '+px(Q.open));c.querySelector('.v').style.fontSize='1.35rem';return c})(),stat('Previous close',px(Q.prev_close),'bid '+px(Q.bid)+' / ask '+px(Q.ask)),
  stat('Volume',num(Q.volume),'shares today'),stat('Market cap',money(cap),C&&C.shares_outstanding?num(C.shares_outstanding)+' shares':'share count unavailable'),
  stat('IV (30d)',Q.iv30==null?'-':Q.iv30.toFixed(1)+'%',Q.iv30_change==null?'':(Q.iv30_change>0?'+':'')+Q.iv30_change.toFixed(2)+' today'))}
function stat(k,v,d){const c=el('div',null,'card stat');c.append(el('div',k,'k'),el('div',v,'v'),el('div',d||'','d mut'));return c}
(async()=>{try{Q=await api('/api/quote/'+T);drawQuote()}catch(e){$('msg').textContent='No quote for '+T+': '+e.message}})();
(async()=>{try{C=await api('/api/company/'+T);if(C){document.title=T+' - '+C.name;
  $('co').replaceChildren(el('span',C.name),el('span',' · '+C.exchange+(C.industry?' · '+C.industry:''),'mut'));drawQuote()}else $('co').textContent='No SEC company record (ETF, fund or foreign issuer)'}
 catch(e){$('co').textContent=''}})();
const OV=[
 ['vwap','VWAP',[['vwap','#ff9f1a',2,0]]],
 ['vbands','VWAP bands (±1σ, ±2σ)',[['vwap_upper1','#ff9f1a99',1,2],['vwap_lower1','#ff9f1a99',1,2],['vwap_upper2','#ff9f1a55',1,1],['vwap_lower2','#ff9f1a55',1,1]]],
 ['cloud','EMA cloud (8 / 21)',[['cloud_fast','#3fb950',1,0],['cloud_slow','#f85149',1,0]]],
 ['vwma','VWMA 20 (volume-weighted MA)',[['vwma20','#22d3ee',2,0]]],
 ['vwema','VWEMA 20 (volume-weighted EMA)',[['vwema20','#c084fc',2,0]]],
 ['ema9','EMA 9',[['ema9','#facc15',1,0]]],['ema21','EMA 21',[['ema21','#fb923c',1,0]]],
 ['sma20','SMA 20',[['sma20','#60a5fa',1,0]]],['sma50','SMA 50',[['sma50','#a78bfa',1,0]]],['sma200','SMA 200',[['sma200','#f472b6',2,0]]],
 ['bb','Bollinger bands (20, 2)',[['bb_upper','#94a3b8',1,2],['bb_mid','#94a3b866',1,0],['bb_lower','#94a3b8',1,2]]]];
const PN=[['rsi','RSI (14)'],['macd','MACD (12, 26, 9)'],['vmom','VWAP momentum (% from VWAP)']];
const IND_KEY='sm_ind';
function loadSel(){try{const s=JSON.parse(localStorage.getItem(IND_KEY)||'null');if(s&&Array.isArray(s.on))return new Set(s.on)}catch(e){}return new Set(['vwap','cloud'])}
function saveSel(){try{localStorage.setItem(IND_KEY,JSON.stringify({on:[...sel]}))}catch(e){}}
let chart,cs,vs,tf='1day',sel=loadSel(),anchor=null,anchoring=false,B=[],ID=null,subs=[],unsync=null;
const BG='#0a1527',COPT={autoSize:true,layout:{background:{color:BG},textColor:'#e8eefb'},grid:{vertLines:{color:'#16263f'},horzLines:{color:'#16263f'}},rightPriceScale:{minimumWidth:72},timeScale:{timeVisible:true}};
function buildMenu(){const m=$('indmenu');m.replaceChildren();
 const sec=t=>{const h=el('div',t,'mut sm');h.style.cssText='margin:.4rem 0 .15rem;text-transform:uppercase;letter-spacing:.05em;font-size:.7rem';m.append(h)};
 const row=(k,label)=>{const l=el('label',null,'indrow'),c=document.createElement('input');c.type='checkbox';c.checked=sel.has(k);
  c.onchange=()=>{c.checked?sel.add(k):sel.delete(k);saveSel();render()};l.append(c,el('span',label));m.append(l)};
 sec('On the chart');OV.forEach(o=>row(o[0],o[1]));sec('Panes below');PN.forEach(p=>row(p[0],p[1]));
 sec('VWAP anchor');const a=el('label',null,'indrow'),c=document.createElement('input');c.type='checkbox';c.checked=anchoring;
 c.onchange=()=>{anchoring=c.checked;$('chartmsg').replaceChildren(anchoring?el('div','Click a bar to anchor VWAP there.','mut sm'):'')};a.append(c,el('span','Anchor by clicking a bar'));m.append(a);
 const r=el('button','Reset anchor','tf');r.onclick=()=>{anchor=null;anchoring=false;buildMenu();load()};m.append(r);
 m.append(el('div','Default: each trading day (intraday) or the year start (1day).','mut sm'))}
$('indbtn').onclick=e=>{e.stopPropagation();const m=$('indmenu');m.hidden=!m.hidden};
document.addEventListener('click',e=>{const m=$('indmenu');if(!m.hidden&&!m.contains(e.target))m.hidden=true});
function sdata(k){return (ID&&ID[k])||[]}
function lineOpts(c,w,st){return {color:c,lineWidth:w,lineStyle:st,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false}}
function cloudData(){const f=sdata('cloud_fast'),s=new Map(sdata('cloud_slow').map(p=>[p.time,p.value])),up=[],dn=[];
 for(const p of f){const sv=s.get(p.time);if(sv==null)continue;const bull=p.value>=sv,col=bull?'rgba(63,185,80,0.22)':'rgba(248,81,73,0.22)';
  up.push({time:p.time,value:Math.max(p.value,sv),lineColor:'rgba(0,0,0,0)',topColor:col,bottomColor:col});
  dn.push({time:p.time,value:Math.min(p.value,sv),lineColor:'rgba(0,0,0,0)',topColor:BG,bottomColor:BG})}
 return [up,dn]}
function dropSubs(){if(unsync){unsync();unsync=null}subs.forEach(s=>s.remove());subs=[];$('subcharts').replaceChildren()}
function subChart(label,height){const w=el('div'),t=el('div',label,'mut sm');t.style.cssText='margin:.5rem 0 .1rem';const d=el('div');d.style.height=height+'px';w.append(t,d);$('subcharts').append(w);
 const c=LightweightCharts.createChart(d,COPT);subs.push(c);return c}
function render(){if(!window.LightweightCharts)return;
 if(chart){chart.remove();chart=null}dropSubs();
 chart=LightweightCharts.createChart($('chart'),COPT);
 if(sel.has('cloud')&&ID){const [u,d]=cloudData();const a=chart.addAreaSeries({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,lineWidth:1}),b=chart.addAreaSeries({priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,lineWidth:1});a.setData(u);b.setData(d)}
 cs=chart.addCandlestickSeries();vs=chart.addHistogramSeries({priceScaleId:'',priceFormat:{type:'volume'},color:'#58a6ff55'});vs.priceScale().applyOptions({scaleMargins:{top:.8,bottom:0}});
 cs.setData(B.map(b=>({time:b.time,open:b.open,high:b.high,low:b.low,close:b.close})));vs.setData(B.map(b=>({time:b.time,value:b.volume})));
 if(ID)for(const [k,,lines] of OV){if(!sel.has(k))continue;for(const [name,col,w,st] of lines){chart.addLineSeries(lineOpts(col,w,st)).setData(sdata(name))}}
 chart.subscribeClick(p=>{if(anchoring&&p.time!=null){anchor=p.time;anchoring=false;buildMenu();load()}});
 if(ID){
  if(sel.has('rsi')){const c=subChart('RSI (14)',110),s=c.addLineSeries(lineOpts('#22d3ee',2,0));s.setData(sdata('rsi14'));
   for(const lv of [30,70])s.createPriceLine({price:lv,color:'#64748b',lineWidth:1,lineStyle:2,axisLabelVisible:false})}
  if(sel.has('macd')){const c=subChart('MACD (12, 26, 9)',120),h=c.addHistogramSeries({priceLineVisible:false,lastValueVisible:false});
   h.setData(sdata('macd_hist').map(p=>({time:p.time,value:p.value,color:p.value>=0?'#3fb95099':'#f8514999'})));
   c.addLineSeries(lineOpts('#60a5fa',1,0)).setData(sdata('macd'));c.addLineSeries(lineOpts('#fb923c',1,0)).setData(sdata('macd_signal'))}
  if(sel.has('vmom')){const c=subChart('VWAP momentum (% from VWAP)',110),h=c.addHistogramSeries({priceLineVisible:false,lastValueVisible:false});
   h.setData(sdata('vwap_momentum').map(p=>({time:p.time,value:p.value,color:p.value>=0?'#3fb950':'#f85149'})))}
 }
 if(subs.length){const ts=chart.timeScale(),f=r=>{if(r)subs.forEach(c=>c.timeScale().setVisibleLogicalRange(r))};ts.subscribeVisibleLogicalRangeChange(f);unsync=()=>{try{ts.unsubscribeVisibleLogicalRangeChange(f)}catch(e){}}}
 chart.timeScale().fitContent()}
async function load(){const m=$('chartmsg');if(!anchoring)m.textContent='';
 if(!window.LightweightCharts){m.append(el('div','chart library failed to load','err'));return}
 try{B=await api('/api/bars/'+T+'?tf='+tf)}catch(e){B=[];ID=null;render();fail(m,e);return}
 try{ID=await api('/api/indicators/'+T+'?tf='+tf+(anchor!=null?'&anchor='+encodeURIComponent(anchor):''))}catch(e){ID=null;m.append(el('div','Indicators unavailable: '+e.message,'err'))}
 render()}
for(const t of ['15m','1h','4h','1day']){const b=el('button',t,'tf'+(t===tf?' on':''));b.onclick=()=>{tf=t;anchor=null;document.querySelectorAll('#tfs .tf').forEach(x=>x.classList.toggle('on',x===b));load()};$('tfs').append(b)}
buildMenu();load();
(async()=>{const b=$('news');try{const n=await api('/api/news/'+T);if(!n.length)return none(b,'No recent headlines');const u=el('ul');
 for(const x of n){const li=el('li'),h=safeUrl(x.url),a=el('a',x.headline);if(h){a.href=h;a.target='_blank';a.rel='noopener noreferrer'}li.append(a,el('div',(x.source||'')+(x.datetime?' · '+x.datetime.slice(0,22):''),'mut sm'));u.append(li)}b.replaceChildren(u)}catch(e){fail(b,e)}})();
(async()=>{const b=$('opts');try{const o=await api('/api/options/'+T);if(!o)return none(b,'No listed options');const c=o.cp;const m=x=>(x/1e6).toFixed(1)+'M';
 b.replaceChildren(kv([['Expiration',o.expiration+(o.zero_dte?' (0DTE)':'')],['Spot',px(o.spot)],['Net GEX per 1%',m(o.gex.net_gex),cls(o.gex.net_gex)],['Call GEX',m(o.gex.call_gex)],['Put GEX',m(o.gex.put_gex)],
  ['Call volume',num(c.call_volume)],['Put volume',num(c.put_volume)],['Put/Call volume',c.volume_ratio==null?'-':String(c.volume_ratio)],['Call/Put open int.',c.oi_ratio==null?'-':String(c.oi_ratio)],['Contracts',String(o.chain.length)]]))}catch(e){none(b,'No options data for this symbol (not optionable, or the feed is unavailable).')}})();
(async()=>{const b=$('therm');try{const t=await api('/api/valuation/'+T);if(!t)return none(b,'Not enough data for a thermometer (the reference snapshot covers the S&P 500; other stocks need SEC earnings data).');
 const sc=t.score,col=t.label==='cheap'?'var(--up)':t.label==='expensive'?'var(--dn)':'#d4a72c';
 const bar=el('div');bar.style.cssText='position:relative;height:14px;border-radius:7px;margin:.7rem 0 .3rem;background:linear-gradient(90deg,var(--dn),#d4a72c 50%,var(--up))';
 if(sc!=null){const k=el('div');k.style.cssText='position:absolute;top:-4px;width:4px;height:22px;background:#fff;border-radius:2px;left:calc('+Math.min(98,Math.max(1,sc))+'% - 2px)';bar.append(k)}
 const ends=el('div',null,'mut sm');ends.style.cssText='display:flex;justify-content:space-between';ends.append(el('span','pricey'),el('span','cheap'));
 const head=el('div',sc==null?'n/a':(t.label==='cheap'?'Cheap':t.label==='expensive'?'Expensive':'Fairly priced')+' · '+sc+'/100',null);head.style.cssText='font-size:1.25rem;font-weight:700;color:'+col;
 const d=el('div');d.append(head,el('div',t.sector?'against '+t.sector+' peers in the S&P 500':'against the whole S&P 500 (no sector peers known)','mut sm'),bar,ends);
 d.append(table(['Ratio','Value','Sector median','Cheaper than'],t.ratios.map(r=>[r.name,r.value==null?'-':String(r.value),r.sector_median==null?'-':String(r.sector_median),r.cheaper_than_sector_pct==null?'-':r.cheaper_than_sector_pct+'% of peers']),[1,2,3]));
 if(t.quadrant){const q=el('div','Value + quality: '+t.quadrant+(t.quality_pct!=null?' (quality '+t.quality_pct+'%)':''),'sm');q.style.marginTop='.5rem';d.append(q)}
 const n=el('div',(t.live_pe!=null?'P/E uses the live price and SEC earnings ('+t.live_pe+'); ':'')+'P/B and P/S come from a reference snapshot, so they can be dated. Cheap is not a buy signal: low-quality businesses are cheap for a reason. ','mut sm');n.style.marginTop='.5rem';n.append(link('Value + quality screener →','/valuation'));d.append(n);
 b.replaceChildren(d)}catch(e){fail(b,e)}})();
(async()=>{const b=$('fund');try{const f=await api('/api/fundamentals/'+T);if(!f)return none(b,'No SEC financial data (ETFs, funds and many foreign issuers do not file it).');
 const p=v=>v==null?'-':v.toFixed(1)+'%';
 b.replaceChildren(kv([['P/E (last 12 months)',f.pe==null?(f.eps_ttm!=null&&f.eps_ttm<=0?'not profitable':'-'):f.pe.toFixed(1)],['Earnings yield',p(f.earnings_yield_pct)],['Revenue (12 months)',money(f.revenue_ttm)],
  ['Revenue growth, last fiscal year',p(f.revenue_growth_pct)],['Operating margin',p(f.op_margin_pct)],['Net margin',p(f.net_margin_pct)],['Return on equity',p(f.roe_pct)],
  ['Debt / equity',f.debt_to_equity==null?'-':f.debt_to_equity.toFixed(2)],['Net debt',money(f.net_debt)]]),el('div','SEC XBRL filings, period ending '+(f.period_end||'-')+'. Trailing 12 months = last fiscal year + this year to date - same period last year.','mut sm'))}catch(e){none(b,'Financial data unavailable.')}})();
(async()=>{const b=$('flow');try{const f=await api('/api/option-flow/'+T);if(!f)return none(b,'No listed options');const d=el('div');
 for(const x of f.signals)d.append(el('div',x,'sm'));
 if(f.term.length){d.append(el('div','Implied volatility at the money',null));d.lastChild.style.cssText='margin-top:.6rem;font-weight:600';
  d.append(table(['Expiry','Days','IV'],f.term.map(t=>[t.expiration,String(t.dte),t.atm_iv_pct.toFixed(1)+'%']),[1,2]))}
 if(f.unusual.length){d.append(el('div','Unusual contracts (volume far above open interest)'));d.lastChild.style.cssText='margin-top:.6rem;font-weight:600';
  d.append(table(['Contract','Volume','Open int.','Premium'],f.unusual.map(u=>[u.expiration+' '+u.strike+' '+u.type,num(u.volume),num(u.open_interest),money(u.premium)]),[1,2,3]))}
 b.replaceChildren(d)}catch(e){none(b,'No options flow available for this symbol.')}})();
(async()=>{const b=$('analyst');try{const a=await api('/api/analyst/'+T);if(!a)return none(b,'No analyst coverage (or FINNHUB_API_KEY is not set).');const tot=a.buy+a.hold+a.sell||1,bar=el('div');bar.style.cssText='display:flex;height:10px;border-radius:5px;overflow:hidden;margin:.5rem 0';
 for(const [n,c] of [[a.buy,'var(--up)'],[a.hold,'var(--mut)'],[a.sell,'var(--dn)']]){const d=el('div');d.style.cssText='width:'+n/tot*100+'%;background:'+c;bar.append(d)}
 b.replaceChildren(el('div',a.verdict,'v '+(a.verdict==='Buy'?'up':a.verdict==='Sell'?'dn':'mut')),bar,el('div','Buy '+a.buy+' · Hold '+a.hold+' · Sell '+a.sell+' ('+a.period+')','mut sm'))}catch(e){fail(b,e)}})();
(async()=>{const b=$('inst');try{const d=await api('/api/investors/'+T+'?limit=8');const s=d.summary;
 if(!s.filerCount)return none(b,'No 13F holders found');
 const head=el('div',s.filerCount.toLocaleString()+' institutions hold '+(s.heldPct==null?num(s.stockShares)+' shares':s.heldPct+'% of the company')+' ('+d.coverage.quarter+').','sm');
 const rows=d.data.map(r=>{const n=/^[0-9]{1,10}$/.test(r.cik)?link(r.name,'/institutional-investor/manager/'+r.cik):r.name;
  return [n,num(r.shares),r.ownershipPct==null?'-':r.ownershipPct.toFixed(2)+'%',(r.shareChange>0?'+':'')+num(r.shareChange)]});
 const more=link('All '+s.filerCount.toLocaleString()+' investors →','/stock/'+T+'/investors');more.style.display='inline-block';more.style.marginTop='.5rem';
 b.replaceChildren(head,table(['Investor','Shares','Owns','Change'],rows,[1,2,3]),more)}catch(e){fail(b,e)}})();
(async()=>{const b=$('ins');try{const d=await api('/api/insider-trades/'+T);if(!d.trades.length)return none(b,'No open-market insider trades in '+d.quarter);
 const rows=d.trades.slice(0,10).map(r=>[fdate(r.date),r.owner,r.role,el('span',r.side.toUpperCase(),cls(r.side==='buy'?1:-1)),num(r.shares),'$'+px(r.price),money(r.value)]);
 b.replaceChildren(table(['Date','Insider','Role','Side','Shares','Price','Value'],rows,[4,5,6]),el('div','SEC Form 4 data set, '+d.quarter+'. Open-market trades only.','mut sm'))}catch(e){fail(b,e)}})();
(async()=>{const b=$('pol');try{const d=await api('/api/political-trades?ticker='+T+'&days=365&limit=10');if(!d.latest.length)return none(b,'No House member trades in the last year');
 const rows=d.latest.map(r=>[fdate(r.date),link(r.member,'/political-trades?member='+encodeURIComponent(r.member)),r.type,r.amount_high?money(r.amount_low)+' – '+money(r.amount_high):'Over '+money(r.amount_low)]);
 b.replaceChildren(table(['Traded','Member','Type','Amount'],rows,[]))}catch(e){fail(b,e)}})();
(async()=>{const b=$('dark');try{const d=await api('/api/dark-pool/'+T);if(!d.venues.length)return none(b,'No ATS volume reported for the week of '+fdate(d.week));
 const rows=d.venues.slice(0,8).map(v=>[v.name,num(v.shares),v.share_pct.toFixed(1)+'%']);
 b.replaceChildren(el('div','Week of '+fdate(d.week)+' (FINRA, ~3 weeks delayed)','mut sm'),table(['Venue','Shares','Share'],rows,[1,2]))}catch(e){fail(b,e)}})();
(async()=>{const b=$('shv');try{const x=await api('/api/short-volume/'+T);if(!x)return none(b,'No data for '+T);
 b.replaceChildren(kv([['Date',x.date],['Short ratio',x.short_ratio==null?'-':(x.short_ratio*100).toFixed(1)+'%'],['Short volume',num(x.short_volume)],['Total volume',num(x.total_volume)]]),
  el('div','Share of daily volume that was short sales (not short interest).','mut sm'))}catch(e){fail(b,e)}})();
"""


def render_stock(ticker):
    import re
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker):
        raise ValueError("bad ticker")
    return shell(f"{ticker} stock", "dash", _STOCK_BODY.replace("__T__", ticker), _STOCK_JS.replace("__T__", ticker),
                 _MANAGER_CSS + _SM_CSS + _LIST_CSS + _STOCK_CSS)


# ------------------------------------------------------------------ portfolio lab
_LAB_CSS = r"""
.form{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.7rem;align-items:end}
.form label{display:block;font-size:.65rem;letter-spacing:.07em;text-transform:uppercase;color:var(--mut);margin-bottom:.2rem}
.form input,.form select{width:100%;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.45rem .6rem;font:inherit}
.chk{display:flex;gap:.6rem;align-items:flex-start;padding:.5rem 0;border-top:1px solid var(--line)}.chk:first-child{border-top:0}
.chk b{font-size:.7rem;padding:.1rem .45rem;border-radius:5px;flex:none}.chk .ok{background:#0c3b2c;color:#22c58b}.chk .no{background:#451a1a;color:#f0524f}
.leg{display:flex;gap:1rem;flex-wrap:wrap;font-size:.78rem;margin-top:.4rem}.leg i{display:inline-block;width:18px;height:3px;margin-right:.35rem;vertical-align:middle}
.wbar{display:inline-block;height:8px;background:var(--acc);border-radius:4px;vertical-align:middle;margin-right:.4rem}
"""

_LAB_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Portfolio lab</h1>
 <p class="mut">Walk-forward test of portfolio optimisation (mean-variance, turnover costs, shrinkage, CVaR) against equal weights and the S&amp;P 500,
 on real adjusted prices, net of costs. Parameters are tuned on a validation period; the final test runs once. Acceptance criteria are fixed before it runs.
 Research tool, not investment advice.</p>
 <section class="card"><form id="f" class="form">
  <div><label for="u">Universe</label><select id="u"><option value="document">Document: 10 S&amp;P 500 companies</option>
   <option value="most_held">Most held by the top-100 funds</option><option value="insider_buys">Biggest insider buys (30 days)</option>
   <option value="watchlist">Dashboard watchlist</option><option value="custom">Custom tickers</option></select></div>
  <div id="cw" hidden><label for="c">Tickers</label><input id="c" placeholder="AAPL MSFT NVDA ..." maxlength="300"></div>
  <div><label for="y">History</label><select id="y"><option value="5">5 years</option><option value="10" selected>10 years</option></select></div>
  <div><label for="b">Cost per trade (bps)</label><input id="b" type="number" min="0" max="100" step="1" value="5"></div>
  <div><label for="p">Max weight per stock (%)</label><input id="p" type="number" min="5" max="100" step="5" value="35"></div>
  <div><button class="btn on" id="go" type="submit">Run study</button></div>
 </form><div id="st" class="mut" style="margin-top:.6rem"></div><div id="msg" class="err"></div></section>
 <div id="out"></div>
 <section class="card" style="margin-top:1rem"><h3>Previous runs</h3><div id="runs" class="mut">None yet</div></section>
</div>
"""

_LAB_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const pc=v=>v==null?'-':(v*100).toFixed(2)+'%',sh=v=>v==null?'-':v.toFixed(2);
async function api(p,body){const r=await fetch(p,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined),j=await r.json();
 if(!r.ok)throw new Error(j.error||r.status);return j}
const NAMES={equal_weight:'Equal weights',mean_variance:'Mean-variance',mv_costs:'Mean-variance + turnover costs',extended:'Extended (shrinkage, cap, costs)',cvar:'CVaR',benchmark:'S&P 500'};
const COL={equal_weight:'#8497b5',mean_variance:'#ffa64d',mv_costs:'#a78bfa',extended:'#1fa3ff',cvar:'#22c58b',benchmark:'#f0524f'};
$('u').onchange=()=>{$('cw').hidden=$('u').value!=='custom'};
function chart(c){const W=820,H=280,L=48,B=24,T=10,ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('width','100%');
 const all=Object.values(c.models).flat(),lo=Math.min(...all)*.98,hi=Math.max(...all)*1.02,n=c.dates.length;
 const X=i=>L+i*(W-L-8)/Math.max(n-1,1),Y=v=>T+(H-T-B)*(1-(v-lo)/(hi-lo));
 const mk=(t,a)=>{const e=document.createElementNS(ns,t);for(const k in a)e.setAttribute(k,a[k]);return e};
 for(let g=0;g<=4;g++){const v=lo+(hi-lo)*g/4,y=Y(v);svg.append(mk('line',{x1:L,x2:W-8,y1:y,y2:y,stroke:'#16263f'}));const t=mk('text',{x:L-6,y:y+4,'text-anchor':'end',fill:'#8497b5','font-size':11});t.textContent=v.toFixed(2);svg.append(t)}
 for(const k in c.models){const d=c.models[k].map((v,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)).join(' ');
  svg.append(mk('path',{d,fill:'none',stroke:COL[k]||'#fff','stroke-width':k==='extended'?2.6:1.4,'stroke-dasharray':k==='benchmark'?'4 3':'0'}))}
 for(const i of [0,Math.floor(n/2),n-1]){const t=mk('text',{x:X(i),y:H-6,'text-anchor':i===0?'start':i===n-1?'end':'middle',fill:'#8497b5','font-size':11});t.textContent=c.dates[i];svg.append(t)}
 const box=el('div');box.append(svg);const lg=el('div',null,'leg');
 for(const k in c.models){const s=el('span'),i=el('i');i.style.background=COL[k]||'#fff';s.append(i,document.createTextNode(NAMES[k]||k));lg.append(s)}box.append(lg);return box}
function section(title,node){const s=el('section',null,'card');s.style.marginTop='1rem';s.append(el('h3',title),node);return s}
function table(head,rows){const t=el('table',null,'t'),h=el('tr');head.forEach((x,i)=>{const th=el('th',x);if(i)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);
 const tb=el('tbody');for(const r of rows){const tr=el('tr');r.forEach((c,i)=>{const td=c instanceof Node?(()=>{const d=el('td');d.append(c);return d})():el('td',c);if(i)td.classList.add('n');tr.append(td)});tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
function show(r){const out=$('out');out.replaceChildren();const p=r.periods,m=r.test.models;
 if((r.warnings||[]).length){const w=el('section',null,'card');w.style.borderColor='#ffb347';w.append(el('h3','Warnings'));for(const x of r.warnings)w.append(el('div',x,'mut'));out.append(w)}
 out.append(section('Acceptance criteria (fixed before the test)',(()=>{const d=el('div');for(const a of r.acceptance){const row=el('div',null,'chk'),b=el('b',a.pass?'PASS':'FAIL',a.pass?'ok':'no'),x=el('div');x.append(el('div',a.text),el('div',a.detail,'mut'));row.append(b,x);d.append(row)}return d})()));
 const keys=['equal_weight','mean_variance','mv_costs','extended','cvar','benchmark'];
 out.append(section('Final test, net of costs ('+p.validation_end+' to '+p.end+', '+p.test_days+' days)',
  table(['Model','Annual return','Volatility','Sharpe','Max drawdown','CVaR 95% (day)','Avg turnover','Costs paid'],keys.map(k=>[NAMES[k],pc(m[k].ann_return),pc(m[k].ann_vol),sh(m[k].sharpe),pc(m[k].max_drawdown),pc(m[k].cvar95),pc(m[k].avg_turnover),pc(m[k].cost_total)]))));
 out.append(section('Growth of 1 on the test days',chart(r.curves)));
 const tk=r.tickers;
 out.append(section('Weights (latest rebalance)',table(['Stock','Equal','Mean-variance','+ costs','Extended','CVaR','Average (extended)'],tk.map(t=>{const w=r.weights,a=el('span');a.append(tkLink(t));
  const bar=v=>{const s=el('span');const b=el('span',null,'wbar');b.style.width=Math.round(v*120)+'px';s.append(b,document.createTextNode((v*100).toFixed(1)+'%'));return s};
  return [a,(w.equal_weight[t]*100).toFixed(1)+'%',(w.mean_variance[t]*100).toFixed(1)+'%',(w.mv_costs[t]*100).toFixed(1)+'%',bar(w.extended[t]),(w.cvar[t]*100).toFixed(1)+'%',(r.average_weights[t]*100).toFixed(1)+'%']}))));
 out.append(section('The six questions of the case study',(()=>{const d=el('div');for(const a of r.answers){const x=el('div',null,'chk'),y=el('div');y.append(el('b',a.question),el('div',a.answer,'mut'));x.append(y);d.append(x)}return d})()));
 const sel=r.validation.selected;
 out.append(section('Chosen on the validation period',table(['Model','lambda','kappa','Validation Sharpe'],Object.keys(sel).map(k=>[NAMES[k],String(sel[k].lam),sel[k].kappa==null?'-':String(sel[k].kappa),sh(sel[k].sharpe)]))));
 const files=el('div');for(const f of ['report.md','metrics.json','weights.csv','returns.csv','config.json','data_manifest.json']){const a=el('a',f);a.href='/api/lab/file/'+r.run_id+'/'+f;a.style.marginRight='1rem';files.append(a)}
 out.append(section('Audit files ('+r.manifest.rows+' days of data, sha256 '+r.manifest.sha256.slice(0,12)+')',files));
 out.append(el('p',r.notice,'note'))}
async function open_(id){try{const r=await api('/api/lab/result/'+id);r.run_id=id;show(r);window.scrollTo({top:$('out').offsetTop-80,behavior:'smooth'})}catch(e){$('msg').textContent=e.message}}
function drawRuns(runs){const b=$('runs');if(!runs.length){b.textContent='None yet';return}
 b.replaceChildren(table(['Run','Universe','Stocks','Criteria passed','Extended Sharpe','Equal Sharpe'],runs.map(r=>{const a=el('a',r.id);a.href='#';a.onclick=e=>{e.preventDefault();open_(r.id)};
  return [a,r.universe,r.tickers.length+' ('+r.tickers.slice(0,5).join(', ')+(r.tickers.length>5?'…':'')+')',r.passed+' / '+r.criteria,sh(r.extended_sharpe),sh(r.equal_sharpe)]})))}
let last=null;
async function poll(){try{const s=await api('/api/lab/status');drawRuns(s.runs);const st=s.status;
  $('st').textContent=st.state==='running'?'Running: '+st.message+'… (a few minutes)':'';$('go').disabled=st.state==='running';
  if(st.state==='error')$('msg').textContent=st.message;
  if(st.state==='running'){setTimeout(poll,3000)}else if(st.run_id&&st.state==='done'&&st.run_id!==last){last=st.run_id;open_(st.run_id)}}catch(e){$('msg').textContent=e.message}}
$('f').onsubmit=async e=>{e.preventDefault();$('msg').textContent='';
 try{await api('/api/lab/run',{universe:$('u').value,custom:$('c').value,years:+$('y').value,cost_bps:+$('b').value,cap:+$('p').value/100});poll()}catch(x){$('msg').textContent=x.message}};
poll();
"""


def render_lab():
    return shell("Portfolio lab", "lab", _LAB_BODY, _LAB_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS + _LAB_CSS)


# ------------------------------------------------------------------ automatic picks
_PICKS_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Top 10 stocks and ETFs to consider</h1>
 <p class="mut">Built automatically from public data and refreshed every few hours: what the 100 biggest funds are buying, insider and House purchases,
 price momentum, trend and risk. A screen to start research from, not investment advice. The page also shows how the price part of the rule did in the past.</p>
 <div id="view"></div>
</div>
"""

_PICKS_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const pc=v=>v==null?'-':(v*100).toFixed(1)+'%',sg=v=>v==null?'-':(v>=0?'+':'')+(v*100).toFixed(0)+'%',sh=v=>v==null?'-':v.toFixed(2);
const SIGNAME={momentum:'momentum',trend:'trend',quality:'risk-adjusted',smart:'funds',insider:'insiders',politician:'House',drawdown:'near high'};
function chips(sig){const d=el('div',null,'chips');for(const k of Object.keys(sig)){const v=sig[k];if(v==null||Math.abs(v)<0.5)continue;
 const c=el('span',(v>0?'+ ':'- ')+SIGNAME[k],'sig '+(v>0?'up':'dn'));d.append(c)}return d}
function pickTable(rows,etf){const t=el('table',null,'t'),h=el('tr');
 for(const x of ['#',etf?'ETF':'Stock','Score','Weight','Price','12 months','Why']){const th=el('th',x);if(['Score','Weight','Price','12 months'].includes(x))th.className='n';h.append(th)}
 const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
 for(const p of rows){const tr=el('tr'),n=el('td'),a=tkLink(p.ticker);n.append(a,el('div',p.name+(p.category?' · '+p.category.replace('_',' '):''),'mut sm'));
  const why=el('td');for(const r of p.reasons)why.append(el('div',r,'sm'));why.append(chips(p.signals));
  tr.append(el('td',String(p.rank)),n,el('td',p.score.toFixed(2),'n'),el('td',(p.weight*100).toFixed(0)+'%','n'),el('td','$'+p.price.toFixed(2),'n'),
   el('td',sg(p.features.ret_12_1),'n '+(p.features.ret_12_1>=0?'up':'dn')),why);tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
function sec(title,node,note){const s=el('section',null,'card');s.style.marginTop='1rem';s.append(el('h3',title),node);if(note)s.append(el('div',note,'note'));return s}
function curve(c){const W=820,H=240,L=44,B=22,T=8,ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('width','100%');
 const all=Object.values(c.models).flat(),lo=Math.min(...all)*.98,hi=Math.max(...all)*1.02,n=c.dates.length,X=i=>L+i*(W-L-8)/Math.max(n-1,1),Y=v=>T+(H-T-B)*(1-(v-lo)/(hi-lo));
 const mk=(t,a)=>{const e=document.createElementNS(ns,t);for(const k in a)e.setAttribute(k,a[k]);return e};
 const col={picks_rule:'#1fa3ff',equal_weight:'#8497b5',benchmark:'#f0524f'};
 for(let g=0;g<=3;g++){const v=lo+(hi-lo)*g/3,y=Y(v);svg.append(mk('line',{x1:L,x2:W-8,y1:y,y2:y,stroke:'#16263f'}));const t=mk('text',{x:L-5,y:y+4,'text-anchor':'end',fill:'#8497b5','font-size':11});t.textContent=v.toFixed(2);svg.append(t)}
 for(const k in c.models)svg.append(mk('path',{d:c.models[k].map((v,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)).join(' '),fill:'none',stroke:col[k],'stroke-width':k==='picks_rule'?2.4:1.4,'stroke-dasharray':k==='benchmark'?'4 3':'0'}));
 for(const i of [0,n-1]){const t=mk('text',{x:X(i),y:H-5,'text-anchor':i?'end':'start',fill:'#8497b5','font-size':11});t.textContent=c.dates[i];svg.append(t)}
 const box=el('div');box.append(svg);return box}
function regimeCard(g){const L={risk_on:['Risk-on','#22c58b'],caution:['Caution','#ffb347'],risk_off:['Risk-off','#f0524f']}[g.label],box=el('div');
 const h=el('div');h.style.cssText='display:flex;align-items:center;gap:.8rem;flex-wrap:wrap';const chip=el('span',L[0]);chip.style.cssText='font-weight:800;font-size:1.1rem;color:'+L[1];h.append(chip,el('span','since '+g.since+' · S&P 500 as of '+g.as_of,'mut sm'));box.append(h);
 for(const r of g.reasons)box.append(el('div',r,'sm'));box.append(el('div',g.advice,'sm'));
 if(g.backtest){const t=el('div',g.backtest.verdict_text+' ('+g.backtest.time_in_market_pct.toFixed(0)+'% of the time invested.)','sm');t.style.marginTop='.5rem';box.append(t)}
 return box}
function render(d){const w=el('div');
 if(d.regime)w.append(sec('Market regime (S&P 500)',regimeCard(d.regime),'A rule tested on the past, not a forecast. Regimes change; one index and a few episodes prove little.'));
 w.append(sec('Top '+d.stocks.length+' stocks',pickTable(d.stocks,false),'Among the '+d.pool.stocks+' most widely held stocks of the top funds ('+d.pool.stocks_scored+' passed the filters). Weights: inverse volatility, at most '+Math.round(d.method.max_weight*100)+'% each. Prices as of '+d.as_of+'.'));
 w.append(sec('Top '+d.etfs.length+' ETFs',pickTable(d.etfs,true),'From '+d.pool.etfs+' ETFs (broad catalogue plus those the funds hold); leveraged and inverse funds excluded; at most '+d.method.max_per_category+' per category; identical index funds listed once.'));
 const evd=d.evidence;
 if(evd){const V={works:['Works','#22c58b'],not_proven:['Not proven','#ffb347'],negative:['Negative','#f0524f'],too_little_data:['Too little data','#8497b5']};
  const t=el('table',null,'t'),h=el('tr');['Signal','Decided on','Avg rank correlation','t-stat','Top fifth beat the rest by','Dates','Verdict'].forEach((x,i)=>{const th=el('th',x);if(i&&i<6)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
  for(const k of Object.keys(evd.signals)){const g=evd.signals[k],st=g.stats[g.decided_on_days],row=el('tr'),v=V[g.verdict]||[g.verdict,'#8497b5'],vs=el('span',v[0]);vs.style.cssText='font-weight:700;color:'+v[1];const vc=el('td');vc.append(vs);
   row.append(el('td',g.label),el('td',g.decided_on_days+' trading days','n'),el('td',st.mean_ic==null?'-':st.mean_ic.toFixed(3),'n'),el('td',st.ic_t==null?'-':st.ic_t.toFixed(1),'n'),
    el('td',st.top_quintile_excess_pct==null?'-':(st.top_quintile_excess_pct>=0?'+':'')+st.top_quintile_excess_pct.toFixed(1)+' pts','n'),el('td',String(g.n_dates),'n'),vc);tb.append(row)}
  t.append(tb);const w2=el('div',null,'tbl');w2.append(t);const box=el('div');box.append(w2);
  const wt=d.method.weights_source==='evidence'?'The ranking above uses weights scaled by this evidence (weights_source: evidence).':'Not enough quarters yet (need 6): the ranking uses the default weights (weights_source: default).';
  box.append(el('div',wt,'sm'));for(const c of evd.caveats)box.append(el('div',c,'sm mut'));
  w.append(sec('Evidence from the past (point-in-time test of each signal, '+evd.meta.quarters+' quarters)',box,'Rank correlation: do stocks that scored high go on to beat the others? A value near 0 means no predictive power; t-stats above 2 are needed before a signal is called proven. Verdicts: too_little_data, not_proven, works, negative.'))}
 const tr=d.track_record;
 if(tr){const box=el('div');
  if(!tr.rows.length)box.append(el('div','Collecting: '+tr.snapshots+' snapshot(s) saved so far. Today\'s list is saved automatically; results appear from the next day.','mut'));
  else{const a=tr.aggregate,line=(k,l)=>a[k]&&a[k].n?l+': '+a[k].n+' snapshot(s), average '+(a[k].avg_excess_pct>=0?'+':'')+a[k].avg_excess_pct.toFixed(1)+' points vs the S&P 500, beat it '+a[k].hit_rate_pct.toFixed(0)+'% of the time':null;
   for(const [k,l] of [['stocks','Stocks'],['stocks_7d','Stocks, 7+ days old'],['stocks_30d','Stocks, 30+ days old'],['etfs','ETFs'],['etfs_30d','ETFs, 30+ days old']]){const x=line(k,l);if(x)box.append(el('div',x,'sm'))}
   const t=el('table',null,'t'),h=el('tr');['Snapshot','Days','Top 10 stocks','Pool of stocks','Top 10 ETFs','S&P 500'].forEach((x,i)=>{const th=el('th',x);if(i)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
   const f=v=>v==null?'-':(v>=0?'+':'')+v.toFixed(1)+'%';
   for(const r of tr.rows.slice(0,30)){const row=el('tr');row.append(el('td',r.date),el('td',String(r.age_days),'n'),el('td',r.stocks?f(r.stocks.weighted_pct):'-','n'),el('td',r.stocks?f(r.stocks.pool_pct):'-','n'),el('td',r.etfs?f(r.etfs.weighted_pct):'-','n'),el('td',f(r.spy_pct),'n'));tb.append(row)}
   t.append(tb);const w=el('div',null,'tbl');w.append(t);box.append(w)}
  w.append(sec('Live track record (forward only, saved every day)',box,tr.note))}
 const bt=d.backtest;
 if(bt){const m=bt.models,rows=[['picks_rule','The rule (top '+bt.params.top_n+', price signals only)'],['equal_weight','Equal weights, same stocks'],['benchmark','S&P 500']];
  const t=el('table',null,'t'),h=el('tr');['Model','Annual return','Volatility','Sharpe','Max drawdown','Costs paid'].forEach((x,i)=>{const th=el('th',x);if(i)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
  for(const [k,l] of rows){const tr=el('tr');tr.append(el('td',l),el('td',pc(m[k].ann_return),'n'),el('td',pc(m[k].ann_vol),'n'),el('td',sh(m[k].sharpe),'n'),el('td',pc(m[k].max_drawdown),'n'),el('td',pc(m[k].cost_total),'n'));tb.append(tr)}
  t.append(tb);const tw=el('div',null,'tbl');tw.append(t);const box=el('div');box.append(tw,curve(bt.curves));
  w.append(sec('Did the price part of the rule work in the past? ('+bt.periods.start+' to '+bt.periods.end+')',box,bt.caveat+' Fixed in advance, monthly, '+bt.params.cost_bps+' bps costs; nothing was tuned on this period.'))}
 else w.append(sec('Backtest of the rule',el('div',d.backtest_error||'Not available','mut')));
 const how=el('div');for(const [k,v] of Object.entries(d.method.stock_weights)){how.append(el('div',SIGNAME[k]+': '+Math.round(v*100)+'% of a stock\'s score','sm'))}
 how.append(el('div','A stock must trade above its 200-day average to be listed; share classes and near-duplicates are listed once.','sm mut'));
 if(d.skipped_notes.length){const dd=el('details');dd.append(el('summary','Skipped for being duplicates or over the category limit ('+d.skipped_notes.length+')'));for(const x of d.skipped_notes)dd.append(el('div',x,'sm mut'));how.append(dd)}
 w.append(sec('How the ranking works',how,d.notice));return w}
$('view').append(perfView('picks',render));
"""

_PICKS_CSS = r"""
.sm{font-size:.78rem}.chips{display:flex;gap:.3rem;flex-wrap:wrap;margin-top:.25rem}
.sig{font-size:.62rem;font-weight:700;padding:.05rem .4rem;border-radius:5px;background:#12233d}.sig.up{color:#22c58b}.sig.dn{color:#f0524f}
td .sm{max-width:560px}
"""


def render_picks():
    return shell("Top picks", "picks", _PICKS_BODY, _PICKS_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS + _PICKS_CSS)


# ------------------------------------------------------------------ status page
_HEALTH_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Status</h1>
 <p class="mut">What is working right now: background jobs and the free data sources behind the pages. Errors here explain empty or stale pages.</p>
 <div class="stats" id="stats"></div>
 <section class="card"><h3>Background jobs</h3><div id="jobs" class="mut">Checking…</div></section>
 <section class="card" style="margin-top:1rem"><h3>Data sources (tiny test request, cached 5 minutes)</h3><div id="src" class="mut">Checking…</div></section>
 <section class="card" style="margin-top:1rem"><h3>Optional API keys</h3><div id="keys" class="mut"></div><p class="note">Set in the .env file next to run.bat. Only whether a key is set is shown, never the key.</p></section>
</div>
"""

_HEALTH_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const COL={ok:'#22c58b',error:'#f0524f',running:'#ffb347',idle:'#8497b5'};
function rows(list){const t=el('table',null,'t'),h=el('tr');['','Name','Detail','Updated'].forEach(x=>h.append(el('th',x)));const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
 for(const r of list){const tr=el('tr'),d=el('td'),dot=el('span','● '+r.status);dot.style.color=COL[r.status]||'#8497b5';dot.style.fontWeight='700';d.append(dot);
  tr.append(d,el('td',r.name),el('td',r.detail||'-','mut'),el('td',r.updated?r.updated.replace('T',' ').slice(0,19):'-','mut'));tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
async function load(){try{const j=await (await fetch('/api/health')).json();if(j.error)throw new Error(j.error);
  $('stats').replaceChildren(...[['Working',j.summary.ok,'ok'],['Errors',j.summary.error,'error'],['Running',j.summary.running,'running'],['Idle',j.summary.idle,'idle']].map(([k,v,c])=>{const d=el('div',null,'card stat');d.append(el('div',k,'k'),el('div',String(v),'v'),el('div',''));d.querySelector('.v').style.color=COL[c];return d}));
  $('jobs').replaceChildren(rows(j.rows.filter(r=>r.kind==='job')));$('src').replaceChildren(rows(j.rows.filter(r=>r.kind==='source')));
  $('keys').replaceChildren(...Object.entries(j.keys).map(([k,v])=>{const d=el('div',(v?'✔ ':'✘ ')+k,v?'up':'mut');return d}))}
 catch(e){$('jobs').textContent=e.message}}
load();setInterval(load,30000);
"""


def render_health():
    return shell("Status", "health", _HEALTH_BODY, _HEALTH_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)


# ------------------------------------------------------------------ daily brief
_BRIEF_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Daily brief</h1>
 <p class="mut">What changed since the last look: picks that entered or left, insider cluster buys, House purchases, filings of funds you follow,
 and warnings about your own portfolio. New items are highlighted and pushed to Telegram once if it is set up. Not investment advice.</p>
 <div id="msg" class="err"></div><div id="view"></div>
 <section class="card" style="margin-top:1rem"><h3>Earlier briefs</h3><div id="hist" class="mut">-</div></section>
</div>
"""

_BRIEF_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
async function load(){try{const r=await fetch('/api/brief'),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);
  const v=$('view');v.replaceChildren();
  if(!j.latest){v.append(el('div','The first brief is built a few minutes after start-up, once the picks exist.','mut'));return}
  const b=j.latest;v.append(el('div','Brief for '+b.date+' · '+b.new_count+' new item(s) · built '+b.generated.replace('T',' ').slice(0,16)+' UTC','mut'));
  for(const s of b.sections){const c=el('section',null,'card');c.style.marginTop='1rem';c.append(el('h3',s.title));
   if(!s.items.length)c.append(el('div','Nothing to report','mut'));
   for(const it of s.items){const row=el('div',null,'row');row.style.cssText='display:flex;gap:.6rem;align-items:center;padding:.35rem 0;border-top:1px solid var(--line)';
    if(it.new){const n=el('span','NEW','tag');n.style.cssText='background:#0c3b2c;color:#22c58b';row.append(n)}
    if(it.severity==='warn'){const n=el('span','CHECK','tag');n.style.cssText='background:#3a2a0c;color:#ffb347';row.append(n)}
    if(it.ticker){row.append(tkLink(it.ticker))}
    const t=el('span',it.text);if(it.cik&&/^[0-9]{1,10}$/.test(it.cik)){const a=el('a',it.text);a.href='/institutional-investor/manager/'+it.cik;row.append(a)}else row.append(t);c.append(row)}
   v.append(c)}
  $('hist').replaceChildren(...(j.history.slice().reverse().slice(0,30).map(h=>el('div',h.date+' · built '+h.generated.replace('T',' ').slice(0,16)+' · '+h.new_count+' new','sm'))))}
 catch(e){$('msg').textContent=e.message}}
load();setInterval(load,300000);
"""


def render_brief():
    return shell("Daily brief", "brief", _BRIEF_BODY, _BRIEF_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)


# ------------------------------------------------------------------ my portfolio
_MINE_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">My portfolio</h1>
 <p class="mut">Enter what you hold, one position per line: <b>TICKER shares average-cost</b> (cost is optional). It stays on this computer. You get value, profit, risk,
 what the big funds and insiders are doing with your stocks, warnings (also in the daily brief) and alternative weightings. Not investment advice.</p>
 <section class="card"><textarea id="ta" rows="7" spellcheck="false" placeholder="AAPL 25 172.50&#10;MSFT 10 310&#10;SPY 5"
  style="width:100%;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:.6rem;font:13px/1.4 ui-monospace,Consolas,monospace"></textarea>
  <div style="margin-top:.6rem"><button class="btn on" id="save">Save and analyse</button> <span id="st" class="mut"></span><span id="msg" class="err"></span></div></section>
 <div id="out"></div>
</div>
"""

_MINE_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const money=v=>{if(v==null)return '-';const a=Math.abs(v),s=a>=1e9?'$'+(a/1e9).toFixed(2)+'B':a>=1e6?'$'+(a/1e6).toFixed(2)+'M':'$'+Math.round(a).toLocaleString();return (v<0?'-':'')+s};
const pc=(v,d=1)=>v==null?'-':(v>0?'+':'')+v.toFixed(d)+'%',cls=v=>v>0?'up':v<0?'dn':'mut';
async function api(p,body){const r=await fetch(p,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function stat(k,v,d,c){const x=el('div',null,'card stat');x.append(el('div',k,'k'),el('div',v,'v'+(c?' '+c:'')),el('div',d||'','d mut'));return x}
function sec(t,n,note){const s=el('section',null,'card');s.style.marginTop='1rem';s.append(el('h3',t),n);if(note)s.append(el('div',note,'note'));return s}
function table(head,rows){const t=el('table',null,'t'),h=el('tr');head.forEach((x,i)=>{const th=el('th',x);if(i)th.className='n';h.append(th)});const th=el('thead');th.append(h);t.append(th);const tb=el('tbody');
 for(const r of rows){const tr=el('tr');r.forEach((c,i)=>{const td=c instanceof Node?(()=>{const d=el('td');d.append(c);return d})():el('td',c==null?'-':String(c));if(i)td.classList.add('n');tr.append(td)});tb.append(tr)}
 t.append(tb);const w=el('div',null,'tbl');w.append(t);return w}
function show(j){const a=j.analysis,o=$('out');o.replaceChildren();
 if(a.message&&!(a.totals)){o.append(el('p',a.message,'mut'));return}
 const t=a.totals,r=a.risk;
 const st=el('div',null,'stats');st.append(stat('Value',money(t.value),t.priced+' of '+t.of+' positions priced'),stat('Profit / loss',t.pnl==null?'-':money(t.pnl),t.pnl==null?'enter costs to see it':pc(t.pnl_pct),t.pnl==null?'':cls(t.pnl)),
  stat('Volatility (1y)',r?r.vol_pct.toFixed(1)+'%':'-',r?'beta '+(r.beta==null?'-':r.beta.toFixed(2))+' vs S&P 500':''),stat('Worst day-type loss',r?r.cvar95_pct.toFixed(1)+'%':'-','average of the worst 5% of days'),
  stat('Effective positions',r?r.effective_n.toFixed(1):'-','top 3 = '+(r?r.top3_weight_pct.toFixed(0):'-')+'% of value'));o.append(st);
 if(a.warnings.length){const d=el('div');for(const w of a.warnings){const x=el('div',null,'row');x.style.cssText='display:flex;gap:.6rem;padding:.3rem 0;border-top:1px solid var(--line)';const g=el('span','CHECK','tag');g.style.cssText='background:#3a2a0c;color:#ffb347';x.append(g);if(w.ticker)x.append(tkLink(w.ticker));x.append(el('span',w.text));d.append(x)}o.append(sec('Warnings',d))}
 o.append(sec('Positions',table(['Stock','Shares','Price','Value','Weight','Profit / loss','Top funds','Pick rank','Insiders (90d)'],a.positions.map(p=>{const s=el('span');s.append(tkLink(p.ticker));
  return [s,p.shares,p.price==null?(p.note||'-'):'$'+p.price.toFixed(2),money(p.value),p.weight==null?'-':(p.weight*100).toFixed(1)+'%',p.pnl_pct==null?'-':money(p.pnl)+' ('+pc(p.pnl_pct)+')',
   p.funds?p.funds.holders+' ('+(p.funds.change>0?'+':'')+p.funds.change+')':'-',p.pick_rank?'#'+p.pick_rank:'-',p.insider_net==null?'-':(p.insider_net>=0?'bought ':'sold ')+money(Math.abs(p.insider_net))]}))));
 if(a.correlated_pairs.length)o.append(sec('Stocks that move together',table(['Pair','Correlation'],a.correlated_pairs.map(p=>[p.a+' / '+p.b,p.corr.toFixed(2)]))));
 if(a.alternatives.length){const N={current:'Your weights',equal:'Equal weights',inverse_vol:'Inverse volatility',optimized:'Risk-aware optimisation (shrunk, capped, low turnover)'};
  o.append(sec('Alternative weightings (same stocks, last year)',table(['Weighting','Volatility','Worst 5% of days','Max drawdown','1y return'],a.alternatives.map(x=>[N[x.name],x.vol_pct.toFixed(1)+'%',x.cvar95_pct.toFixed(2)+'%',x.max_drawdown_pct.toFixed(1)+'%',pc(x.ret_1y_pct)])),
   'In-sample estimates: they show risk, not what will happen. Past return is shown only for context.'));
  o.append(sec('Trades the optimisation would suggest',table(['Stock','Change in weight','Approx. amount'],a.trades_to_optimized.filter(x=>Math.abs(x.delta_pct)>=1).map(x=>{const s=el('span');s.append(tkLink(x.ticker));return [s,pc(x.delta_pct),money(x.delta_value)]}),
   ),'Suggestions are mechanical, ignore taxes and fees, and rest on noisy estimates; equal or inverse-volatility weights are the more robust references.'))}
 o.append(el('p',a.note,'note'))}
async function load(){try{const j=await api('/api/my-portfolio');$('ta').value=j.positions.map(p=>p.ticker+' '+p.shares+(p.cost==null?'':' '+p.cost)).join('\n');show(j)}catch(e){$('msg').textContent=e.message}}
$('save').onclick=async()=>{$('msg').textContent='';$('st').textContent='Saving and pricing…';
 try{const rows=$('ta').value.split(/\n/).map(l=>l.trim()).filter(Boolean).map(l=>{const p=l.split(/[\s,;]+/);return {ticker:p[0],shares:p[1],cost:p[2]==null?null:p[2]}});
  await api('/api/my-portfolio',{positions:rows});await load()}catch(e){$('msg').textContent=e.message}$('st').textContent=''};
load();
"""


def render_mine():
    return shell("My portfolio", "mine", _MINE_BODY, _MINE_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)


# ------------------------------------------------------------------ value + quality screener
_VAL_BODY = r"""
<div class="wrap">
 <h1 class="title" style="font-size:2rem;margin:.1rem 0 .3rem">Value + quality screener</h1>
 <p class="mut">Cheap is only good if the business is sound. <b>Cheap + quality</b> = candidate; <b>cheap + low quality</b> = value-trap risk.
 Value: how cheap P/E, P/B and P/S are against sector peers. Quality: EBITDA margin against sector peers (return on equity for banks).
 Reference snapshot of the S&amp;P 500 - context for your own judgement, not a buy signal and not investment advice. Click a ticker for its page and thermometer.</p>
 <div id="msg" class="err"></div><div id="tabs" style="margin:.6rem 0"></div>
 <section class="card"><div class="tbl"><table class="t sm"><thead><tr><th>Ticker</th><th>Sector</th><th class="n">P/E</th><th class="n">P/B</th><th class="n">P/S</th><th class="n">EBITDA mg</th><th class="n">Div</th><th class="n">Value %</th><th class="n">Quality %</th><th>Quadrant</th></tr></thead><tbody id="rows"></tbody></table></div></section>
</div>
"""

_VAL_JS = r"""
const $=id=>document.getElementById(id);
const el=(t,x,c)=>{const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e};
const QS=['CHEAP + QUALITY','CHEAP but LOW QUALITY (trap risk)','QUALITY but PRICEY','EXPENSIVE + LOW QUALITY (avoid)'];
const QC={'CHEAP + QUALITY':'var(--up)','CHEAP but LOW QUALITY (trap risk)':'var(--dn)','QUALITY but PRICEY':'#d4a72c','EXPENSIVE + LOW QUALITY (avoid)':'var(--mut)'};
let quad='';
const f=(v,s)=>v==null?'-':v+(s||'');
async function load(){try{const r=await fetch('/api/valuation-screen?limit=120'+(quad?'&quadrant='+encodeURIComponent(quad):'')),j=await r.json();if(!r.ok)throw new Error(j.error||r.status);
  const tabs=$('tabs');tabs.replaceChildren();
  const mk=(q,label)=>{const b=el('button',label,'btn'+(quad===q?' on':''));b.style.marginRight='.4rem';b.onclick=()=>{quad=q;load()};tabs.append(b)};
  mk('','All ('+j.total+')');QS.forEach(q=>mk(q,q+' ('+(j.counts[q]||0)+')'));
  if(!j.total){$('rows').replaceChildren();$('msg').textContent='The fundamentals snapshot (ci_data/sp500_financials.csv) is missing.';return}
  $('msg').textContent='';
  $('rows').replaceChildren(...j.rows.map(x=>{const tr=el('tr');const t=el('td');t.append(tkLink(x.ticker));
   const q=el('td',x.quadrant);q.style.color=QC[x.quadrant]||'var(--mut)';
   tr.append(t,el('td',x.sector),...[f(x.pe),f(x.pb),f(x.ps),f(x.ebitda_margin_pct,'%'),f(x.dividend_pct,'%'),f(x.value_pct),f(x.quality_pct)].map(v=>el('td',v,'n')),q);return tr}))}
 catch(e){$('msg').textContent=e.message}}
load();
"""


def render_valuation():
    return shell("Value + quality", "value", _VAL_BODY, _VAL_JS, _MANAGER_CSS + _SM_CSS + _LIST_CSS)
