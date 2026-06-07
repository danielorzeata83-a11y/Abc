"""Dashboard HTML self-contained 'dip-watch' pentru watchlist: un card per activ,
colorat dupa stare (verde aproape de maxim / galben corectie / rosu dip adanc),
sortat cu cel mai adanc sus. Date inglobate ca JSON + JS vanilla, zero request-uri
externe (merge offline). Refoloseste dip_status validat. NU consiliere de investitii.
"""

import json

import numpy as np

from markov.dipmonitor import DISCLAIMER, dip_status


def dashboard_rows(items, lookback=60, dip=0.4, exit_ma=20):
    """items: list[(nume, close_array)] -> list de randuri pt dashboard, sortate
    cu cel mai adanc drawdown sus (cele 'nodata' la coada)."""
    rows = []
    for name, close in items:
        if close is None or len(close) < lookback + 2:
            rows.append({"name": name, "state": "nodata",
                         "label": "date insuficiente", "price": None,
                         "drawdown": None, "to_threshold": None,
                         "above_ma": False, "fill": 0.0})
            continue
        s = dip_status(close, lookback=lookback, dip=dip, exit_ma=exit_ma)
        dd = s["drawdown"]
        state = ("deep" if s["in_deep_dip"]
                 else "correction" if dd < -0.05 else "near_top")
        fill = float(min(abs(dd) / dip, 1.0) * 100.0) if np.isfinite(dd) else 0.0
        rows.append({"name": name, "state": state, "label": s["label"],
                     "price": round(s["price"], 2), "drawdown": round(dd * 100, 1),
                     "to_threshold": round(abs(s["to_threshold"]) * 100, 1),
                     "above_ma": bool(s["above_exit_ma"]), "fill": round(fill, 1)})
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
.bar{height:8px;background:#2b313b;border-radius:4px;overflow:hidden;margin:6px 0}
.bar>span{display:block;height:100%}
.bar>span.deep{background:var(--red)}
.bar>span.correction{background:var(--yellow)}
.bar>span.near_top{background:var(--green)}
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
    `<div class="bar"><span class="${r.state}" style="width:${r.fill}%"></span></div>`+
    `<div class="label">${r.label} · ${tt}</div>`;
  g.appendChild(c);
}
</script>
</body></html>"""
