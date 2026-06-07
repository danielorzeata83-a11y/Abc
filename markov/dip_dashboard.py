"""Dashboard HTML self-contained 'dip-watch' pentru watchlist: un card per activ,
colorat dupa stare (verde aproape de maxim / galben corectie / rosu dip adanc),
sortat cu cel mai adanc sus. Date inglobate ca JSON + JS vanilla, zero request-uri
externe (merge offline). Refoloseste dip_status validat. NU consiliere de investitii.
"""

import json

import numpy as np

from markov.dipmonitor import DISCLAIMER, dip_status


def _downsample(close, window=250, n=120):
    """Ultimele `window` inchideri, esantionate la cel mult `n` puncte (HTML mic)."""
    close = np.asarray(close, dtype=float)[-window:]
    if len(close) <= n:
        return [round(float(x), 4) for x in close]
    idx = np.linspace(0, len(close) - 1, n).astype(int)
    return [round(float(close[i]), 4) for i in idx]


def _candles(bars, n=80):
    """Ultimele `n` bare OHLC ca [o, h, l, c] (fara esantionare -- lumanari reale)."""
    o = np.asarray(bars.open, dtype=float)[-n:]
    h = np.asarray(bars.high, dtype=float)[-n:]
    l = np.asarray(bars.low, dtype=float)[-n:]
    c = np.asarray(bars.close, dtype=float)[-n:]
    return [[round(float(a), 2), round(float(b), 2), round(float(d), 2),
             round(float(e), 2)] for a, b, d, e in zip(o, h, l, c)]


def _has_ohlc(data):
    return all(hasattr(data, k) for k in ("open", "high", "low", "close"))


def dashboard_rows(items, lookback=60, dip=0.4, exit_ma=20):
    """items: list[(nume, data)], unde data e un Bars (OHLC -> candlestick) sau un
    array de close (-> sparkline). Randuri sortate cu cel mai adanc drawdown sus.
    Fiecare rand: `chart` ('candle'/'line'), `candles` sau `spark`, si `thr`."""
    rows = []
    for name, data in items:
        is_bars = data is not None and _has_ohlc(data)
        close = (np.asarray(data.close, dtype=float) if is_bars
                 else None if data is None else np.asarray(data, dtype=float))
        if close is None or len(close) < lookback + 2:
            rows.append({"name": name, "state": "nodata",
                         "label": "date insuficiente", "price": None,
                         "drawdown": None, "to_threshold": None, "above_ma": False,
                         "fill": 0.0, "chart": "line", "spark": [], "candles": [],
                         "thr": None})
            continue
        s = dip_status(close, lookback=lookback, dip=dip, exit_ma=exit_ma)
        dd = s["drawdown"]
        state = ("deep" if s["in_deep_dip"]
                 else "correction" if dd < -0.05 else "near_top")
        fill = float(min(abs(dd) / dip, 1.0) * 100.0) if np.isfinite(dd) else 0.0
        row = {"name": name, "state": state, "label": s["label"],
               "price": round(s["price"], 2), "drawdown": round(dd * 100, 1),
               "to_threshold": round(abs(s["to_threshold"]) * 100, 1),
               "above_ma": bool(s["above_exit_ma"]), "fill": round(fill, 1),
               "thr": round(s["high"] * (1.0 - dip), 4),
               "spark": [], "candles": []}
        if is_bars:
            row["chart"], row["candles"] = "candle", _candles(data)
        else:
            row["chart"], row["spark"] = "line", _downsample(close)
        rows.append(row)
    rows.sort(key=lambda r: (r["state"] == "nodata",
                             r["drawdown"] if r["drawdown"] is not None else 0.0))
    return rows


def build_html(rows, asof="", dip=0.4, title="Abc — dip-watch"):
    data = json.dumps({"asof": asof, "dip": int(round(dip * 100)), "rows": rows},
                      ensure_ascii=False)
    return (_TEMPLATE.replace("__TITLE__", title)
            .replace("__DISCLAIMER__", DISCLAIMER).replace("__DATA__", data))


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#0e1117;--card:#171b22;--fg:#e6e6e6;--muted:#8b949e;
--green:#2ea043;--yellow:#d29922;--red:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.4 system-ui,Segoe UI,Roboto,sans-serif;padding:16px}
h1{font-size:18px;margin:0 0 2px}
.sub{color:var(--muted);font-size:13px;margin-bottom:14px}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
.card{background:var(--card);border-radius:10px;padding:12px 14px;
border-left:5px solid var(--muted)}
.card.deep{border-color:var(--red)}
.card.correction{border-color:var(--yellow)}
.card.near_top{border-color:var(--green)}
.card.nodata{opacity:.5}
.row1{display:flex;justify-content:space-between;align-items:baseline}
.name{font-weight:700;font-size:16px}
.price{color:var(--muted)}
.dd{font-size:22px;font-weight:700;margin:6px 0}
.dd.deep{color:var(--red)}.dd.correction{color:var(--yellow)}.dd.near_top{color:var(--green)}
.spark{margin:6px 0;line-height:0}
.label{color:var(--muted);font-size:13px}
footer{color:var(--muted);font-size:12px;margin-top:18px;
border-top:1px solid #21262d;padding-top:10px}
</style></head>
<body>
<h1>Abc &mdash; dip-watch</h1>
<div class="sub" id="sub"></div>
<div class="grid" id="grid"></div>
<footer>Regula a fost FRANA DE RISC (drawdown injumatatit in crize), nu accelerator
de profit. Tu decizi. __DISCLAIMER__</footer>
<script>
const D=__DATA__;
const COL={deep:'#f85149',correction:'#d29922',near_top:'#2ea043'};
const W=240,H=44,P=3;
function svg(inner){
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" `+
    `style="width:100%;height:44px">${inner}</svg>`;
}
function thrLine(ty){
  return `<line x1="0" y1="${ty}" x2="${W}" y2="${ty}" stroke="#f85149" `+
    `stroke-dasharray="3 3" stroke-width="1" opacity="0.65"/>`;
}
function spark(r){
  const v=r.spark; if(!v||v.length<2) return '';
  const lo=Math.min(...v,r.thr),hi=Math.max(...v,r.thr),rng=(hi-lo)||1;
  const sx=i=>P+i*(W-2*P)/(v.length-1), sy=val=>P+(hi-val)*(H-2*P)/rng;
  const pts=v.map((val,i)=>sx(i).toFixed(1)+','+sy(val).toFixed(1)).join(' ');
  return svg(thrLine(sy(r.thr).toFixed(1))+
    `<polyline points="${pts}" fill="none" stroke="${COL[r.state]}" stroke-width="1.5"/>`);
}
function candles(r){
  const v=r.candles; if(!v||v.length<1) return '';
  const lo=Math.min(r.thr,...v.map(b=>b[2])), hi=Math.max(r.thr,...v.map(b=>b[1]));
  const rng=(hi-lo)||1, n=v.length, cw=(W-2*P)/n;
  const sy=val=>P+(hi-val)*(H-2*P)/rng;
  let s='';
  v.forEach((b,i)=>{
    const x=P+i*cw+cw/2, col=b[3]>=b[0]?'#2ea043':'#f85149';
    const top=Math.min(sy(b[0]),sy(b[3])), bh=Math.max(0.8,Math.abs(sy(b[3])-sy(b[0])));
    const bw=Math.max(1,cw*0.6);
    s+=`<line x1="${x.toFixed(1)}" y1="${sy(b[1]).toFixed(1)}" x2="${x.toFixed(1)}" `+
       `y2="${sy(b[2]).toFixed(1)}" stroke="${col}" stroke-width="0.7"/>`;
    s+=`<rect x="${(x-bw/2).toFixed(1)}" y="${top.toFixed(1)}" width="${bw.toFixed(1)}" `+
       `height="${bh.toFixed(1)}" fill="${col}"/>`;
  });
  return svg(s+thrLine(sy(r.thr).toFixed(1)));
}
function chart(r){ return r.chart==='candle' ? candles(r) : spark(r); }
document.getElementById('sub').textContent =
  `${D.rows.length} active · prag dip ${D.dip}% sub maxim`+(D.asof?` · ${D.asof}`:'');
const g=document.getElementById('grid');
for(const r of D.rows){
  const c=document.createElement('div'); c.className='card '+r.state;
  if(r.state==='nodata'){
    c.innerHTML=`<div class="row1"><span class="name">${r.name}</span></div>`+
      `<div class="label">${r.label}</div>`; g.appendChild(c); continue;
  }
  const tt = r.state==='deep' ? 'in zona de dip adanc'
    : `mai cade ${r.to_threshold}% pana la prag`;
  c.innerHTML=`<div class="row1"><span class="name">${r.name}</span>`+
    `<span class="price">${r.price}</span></div>`+
    `<div class="dd ${r.state}">${r.drawdown}%</div>`+
    `<div class="spark">${chart(r)}</div>`+
    `<div class="label">${r.label} · ${tt}</div>`;
  g.appendChild(c);
}
</script>
</body></html>"""
