#!/usr/bin/env python3
"""
shared/patch-canales-quarterly.py

Reemplaza la seccion 'Mostrador vs Convenios' en las 7 lineas por una
tabla trimestre x año (texto plano c% / m%, normalizado [0,100]).

Para cada linea:
1. Inyecta D.canales_quarterly = { familia: { year: { Q1..Q4: {c,m,unid} } } }
   filtrado por brands que ya estan en D.canales (mantiene scope por linea).
2. Reemplaza HTML <div id="can-chart"> -> nuevo card con pills + tabla.
3. Inyecta JS: renderCanQuartPills/renderCanQuartTable + listener init.
4. Guarda renderCanales contra #can-chart faltante (no-op silencioso).

Source: shared/canales_quarterly.json (built by user-side script earlier).
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_JSON = REPO / 'shared' / 'canales_quarterly.json'

LINES_DATAJS = ['cardio', 'ATB', 'OTC', 'respiratorio']
LINES_INLINE = {
    'mujer': 'mujer/index.html',
    'SNC':   'SNC/index.html',
    'dermatologia': 'dermatologia/dermato_dashboard.html',
}

OLD_HTML_RE = re.compile(
    r'  <div class="sec" id="s-can">\s*\n'
    r'    <div class="sec-hd">[^\n]*</div>\s*\n'
    r'    <p class="sec-sub">[^\n]*</p>\s*\n'
    r'    <div class="card">\s*\n'
    r'      <div class="can-legend">\s*\n'
    r'        <span><span class="can-sq" style="background:#2563eb"></span>Convenio OS</span>\s*\n'
    r'        <span><span class="can-sq" style="background:#d97706"></span>Mostrador</span>\s*\n'
    r'      </div>\s*\n'
    r'      <div id="can-chart"></div>\s*\n'
    r'    </div>\s*\n'
    r'  </div>'
)

NEW_HTML = '''  <div class="sec" id="s-can">
    <div class="sec-hd"><span class="sec-num">Mostrador vs Convenios</span><h2 class="sec-title">Mostrador vs Convenios</h2></div>
    <p class="sec-sub">% Convenio OS vs Mostrador por trimestre y año · Valores normalizados [0%, 100%]</p>
    <div class="card">
      <div class="pill-group" id="can-quart-pills" style="margin-bottom:18px;"></div>
      <div id="can-quart-table"></div>
    </div>
  </div>'''

JS_BLOCK = r'''
// ── MOSTRADOR vs CONVENIOS (trimestral) ──────────────────────────────
let cqProd = null;
function renderCanQuartPills(){
  const pills = document.getElementById('can-quart-pills'); if(!pills) return;
  const prods = Object.keys(D.canales_quarterly||{}).sort();
  if(!prods.length){ pills.innerHTML='<p style="color:#4b5563;font-size:11px;">Sin datos.</p>'; return; }
  if(!cqProd || !D.canales_quarterly[cqProd]) cqProd = prods[0];
  pills.innerHTML = prods.map(p=>`
    <button class="pill ${p===cqProd?'on':''}" onclick="setCQ('${p.replace(/'/g,"\\'")}')"
      style="${p===cqProd?`color:${(typeof COLORS!=='undefined'&&COLORS[p])||'#b01e1e'};border-color:${(typeof COLORS!=='undefined'&&COLORS[p])||'#b01e1e'}`:''}">
      <span class="dot" style="background:${(typeof COLORS!=='undefined'&&COLORS[p])||'#555'}"></span>${p}
    </button>`).join('');
}
function setCQ(p){
  cqProd=p; renderCanQuartPills(); renderCanQuartTable();
  if(typeof _filterLock!=='undefined' && !_filterLock && typeof PROD_MAP!=='undefined' && PROD_MAP[p] && typeof setGlobalFilter==='function') setGlobalFilter(p);
}
function renderCanQuartTable(){
  const el = document.getElementById('can-quart-table'); if(!el) return;
  const data = (D.canales_quarterly||{})[cqProd];
  if(!data){ el.innerHTML='<p style="color:#4b5563;font-size:11px;padding:8px;">Sin datos para esta marca.</p>'; return; }
  const years = Object.keys(data).sort();
  const quarters = ['Q1','Q2','Q3','Q4'];
  const cellFmt = (v) => {
    if(!v || v.c==null || v.m==null) return '<span style="color:#9ca3af">—</span>';
    return `<span style="color:#2563eb;font-weight:600">${v.c.toFixed(0)}%</span> <span style="color:#9ca3af">/</span> <span style="color:#d97706;font-weight:600">${v.m.toFixed(0)}%</span>`;
  };
  let html = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-family:\'IBM Plex Mono\',monospace;font-size:12px;">';
  html += '<thead><tr><th style="text-align:left;padding:8px 12px;color:#4b5563;font-size:10px;letter-spacing:.1em;text-transform:uppercase;border-bottom:1px solid rgba(0,0,0,.08);">Año</th>';
  for(const q of quarters) html += `<th style="text-align:center;padding:8px 12px;color:#4b5563;font-size:10px;letter-spacing:.1em;text-transform:uppercase;border-bottom:1px solid rgba(0,0,0,.08);">${q}</th>`;
  html += '</tr></thead><tbody>';
  for(const y of years){
    html += `<tr style="border-top:1px solid rgba(0,0,0,.04);"><td style="padding:11px 12px;font-weight:700;color:#111827;font-family:'IBM Plex Mono',monospace;">${y}</td>`;
    for(const q of quarters){
      const v = (data[y]||{})[q];
      html += `<td style="padding:11px 12px;text-align:center;">${cellFmt(v)}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  html += '<p style="margin-top:12px;font-size:10px;color:#6b7280;letter-spacing:.04em;"><span style="color:#2563eb;font-weight:700">■</span> Convenio OS &nbsp;·&nbsp; <span style="color:#d97706;font-weight:700">■</span> Mostrador &nbsp;·&nbsp; Valores normalizados a [0%, 100%]</p>';
  el.innerHTML = html;
}
renderCanQuartPills(); renderCanQuartTable();
'''


def find_d_block(text, is_datajs):
    """Returns (obj_start, D, abs_end, prefix_to_obj_start) for the D block."""
    if is_datajs:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    else:
        m = re.search(r'const\s+D\s*=\s*', text)
    if not m: return None
    obj_start = text.index('{', m.end())
    D, end_off = json.JSONDecoder().raw_decode(text[obj_start:])
    abs_end = obj_start + end_off
    return obj_start, D, abs_end


def patch_data(data_path, is_datajs, source_data):
    """Step 1: inject D.canales_quarterly. Returns brand count."""
    p = REPO / data_path
    text = p.read_text(encoding='utf-8-sig' if is_datajs else 'utf-8', errors='replace')
    pos = find_d_block(text, is_datajs)
    if not pos:
        print(f'  [{data_path}] SKIP: no D block'); return 0
    obj_start, D, abs_end = pos
    existing_brands = list(D.get('canales', {}).keys())
    cq = {}
    for b in existing_brands:
        if b in source_data:
            cq[b] = source_data[b]
    D['canales_quarterly'] = cq
    new_text = text[:obj_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]
    p.write_text(new_text, encoding='utf-8', newline='')
    print(f'  [{data_path}] DATA OK: {len(cq)} brands, {p.stat().st_size:,} bytes')
    return len(cq)


def patch_html_js(html_path):
    """Steps 2-4: HTML replacement + JS injection + guard renderCanales."""
    p = REPO / html_path
    text = p.read_text(encoding='utf-8', errors='replace')
    new_text, n_html = OLD_HTML_RE.subn(NEW_HTML, text, count=1)
    if n_html == 0:
        print(f'  [{html_path}] WARN: HTML pattern not matched')
    if 'renderCanQuartPills' not in new_text:
        inject_at = re.search(r'// ── CONVENIOS', new_text)
        if inject_at:
            new_text = new_text[:inject_at.start()] + JS_BLOCK + '\n' + new_text[inject_at.start():]
            print(f'  [{html_path}] JS injected')
        else:
            print(f'  [{html_path}] WARN: JS anchor not found')
    new_text = re.sub(
        r'(function renderCanales\([^)]*\)\{\n)',
        r"\1  if(!document.getElementById('can-chart'))return;\n",
        new_text,
        count=1
    )
    p.write_text(new_text, encoding='utf-8', newline='')
    print(f'  [{html_path}] HTML+JS OK ({p.stat().st_size:,} bytes)')


def main():
    if not DATA_JSON.is_file():
        print(f'ERROR: {DATA_JSON} no existe', file=sys.stderr); return 2
    source_data = json.loads(DATA_JSON.read_text(encoding='utf-8'))
    print(f'Source: {len(source_data)} familias\n')

    # data.js lines: data lives in data.js, HTML/JS in <line>/index.html
    for line in LINES_DATAJS:
        patch_data(f'{line}/data.js', True, source_data)
        patch_html_js(f'{line}/index.html')
    # inline lines: data + HTML/JS all in one file
    for line, rel in LINES_INLINE.items():
        patch_data(rel, False, source_data)
        patch_html_js(rel)

    print('\nListo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
