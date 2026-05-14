"""Agrega filtro de competidores al Mercado IQVIA en cada dashboard.

UI: pills Top 5 / Top 10 / Solo SIE / Todos + input buscar + lista
toggleable de brands seleccionadas. Filtra el chart y la tabla.

Aplicado en las 7 lineas. Idempotente."""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# CSS
CSS = '''
.perf-bf{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 4px;padding:6px 0;border-top:1px dashed #e5e7eb;}
.perf-bf .lbl{font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6b7280;}
.perf-bf .seg{display:inline-flex;background:#fff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;}
.perf-bf .seg button{padding:4px 9px;border:0;background:transparent;cursor:pointer;font-size:10px;font-weight:600;color:#525252;border-right:1px solid #f3f4f6;font-family:inherit;}
.perf-bf .seg button:last-child{border-right:0;}
.perf-bf .seg button.on{background:#b01e1e;color:#fff;}
.perf-bf input.search{padding:4px 8px;border:1px solid #e5e7eb;border-radius:5px;font-size:11px;width:140px;font-family:inherit;}
.perf-bf .pills{display:flex;gap:4px;flex-wrap:wrap;margin-top:4px;width:100%;}
.perf-bf .pill{padding:2px 7px;border:1px solid #e5e7eb;border-radius:10px;font-size:9px;cursor:pointer;background:#fff;color:#525252;user-select:none;transition:all .12s;}
.perf-bf .pill.on{background:#b01e1e;color:#fff;border-color:#b01e1e;}
.perf-bf .pill.sie{border-color:#b01e1e;font-weight:700;}
'''

# HTML anchor: the perf-metric-ctrl div, we insert filter after it
ANCHOR_HTML = '<div class="seg-ctrl" id="perf-metric-ctrl">'
INJECT_AFTER_CTRLS_PATTERN = re.compile(r'(<div class="seg-ctrl" id="perf-metric-ctrl">.*?</div>)', re.S)
FILTER_HTML = '''
      <div class="perf-bf">
        <span class="lbl">Comparar con</span>
        <div class="seg" id="pf-mode">
          <button data-m="top5">Top 5</button>
          <button data-m="top10" class="on">Top 10</button>
          <button data-m="sie">Solo SIE</button>
          <button data-m="all">Todos</button>
        </div>
        <input type="text" class="search" id="pf-search" placeholder="Buscar marca..." />
        <div class="pills" id="pf-pills"></div>
      </div>'''

# JS state + logic. Inserted at the start of renderPerf body.
JS_STATE = '''
// Brand filter state
window.__sfPF = window.__sfPF || { mode:'top10', selected:new Set(), search:'' };
'''

JS_FILTER_LOGIC = '''
  // Apply brand filter
  if(!window.__sfPF) window.__sfPF = { mode:'top10', selected:new Set(), search:'' };
  const _pf = window.__sfPF;
  // Determine "value" per product for ranking: last period units
  const _rankPK = periodKeys[periodKeys.length-1];
  const _vfn = function(p){
    const v = (pMetric==='ms')
      ? ((pPeriod==='ytd'?p.ms_ytd:pPeriod==='mat'?p.ms_mat:pPeriod==='monthly'?p.ms_monthly:p.ms_quarterly)||{})[_rankPK]
      : ((pPeriod==='monthly'?p.monthly_vals:pPeriod==='ytd'?p.ytd:pPeriod==='mat'?p.mat:p.quarterly_vals)||{})[_rankPK];
    return v||0;
  };
  // Build pills always from full prods
  const _allProds = prods.slice().sort((a,b)=>(_vfn(b)||0)-(_vfn(a)||0));
  // Filter
  let _filtered = _allProds;
  if(_pf.mode==='top5') _filtered = _allProds.slice(0,5);
  else if(_pf.mode==='top10') _filtered = _allProds.slice(0,10);
  else if(_pf.mode==='sie') _filtered = _allProds.filter(p=>p.is_sie);
  // Custom selection (additional filter via pills)
  if(_pf.selected.size > 0){
    _filtered = _allProds.filter(p=>_pf.selected.has(p.prod));
  }
  // Always include SIE
  const _sieProds = _allProds.filter(p=>p.is_sie);
  _sieProds.forEach(s=>{ if(!_filtered.find(x=>x.prod===s.prod)) _filtered.push(s); });
  prods = _filtered;

  // Render pills
  const _pillEl = document.getElementById('pf-pills');
  if(_pillEl){
    const _shown = new Set(_filtered.map(p=>p.prod));
    const q = (_pf.search||'').toLowerCase();
    const _filteredPills = q ? _allProds.filter(p=>p.prod.toLowerCase().includes(q)) : _allProds.slice(0,30);
    _pillEl.innerHTML = _filteredPills.map(p=>{
      const on = _shown.has(p.prod);
      const sie = p.is_sie?' sie':'';
      return `<span class="pill${on?' on':''}${sie}" data-prod="${p.prod.replace(/"/g,'&quot;')}">${p.prod}</span>`;
    }).join('');
  }
'''

JS_WIRING = '''
// Wire perf brand filter (one-time setup)
(function(){
  if(window.__sfPFWired) return;
  window.__sfPFWired = true;
  const ready = function(fn){
    if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  };
  ready(function(){
    const seg = document.getElementById('pf-mode');
    const search = document.getElementById('pf-search');
    const pills = document.getElementById('pf-pills');
    if(seg) seg.addEventListener('click', function(e){
      const b = e.target.closest('button[data-m]');
      if(!b) return;
      seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      window.__sfPF.mode = b.dataset.m;
      window.__sfPF.selected = new Set();
      if(typeof renderPerf==='function') renderPerf();
    });
    if(search) search.addEventListener('input', function(e){
      window.__sfPF.search = e.target.value;
      if(typeof renderPerf==='function') renderPerf();
    });
    if(pills) pills.addEventListener('click', function(e){
      const p = e.target.closest('.pill[data-prod]');
      if(!p) return;
      const prod = p.dataset.prod;
      if(window.__sfPF.selected.has(prod)) window.__sfPF.selected.delete(prod);
      else window.__sfPF.selected.add(prod);
      if(typeof renderPerf==='function') renderPerf();
    });
  });
})();
'''


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if '__sfPF' in t:
        return 'SKIP already'

    # 1) Inject CSS before </style>
    if '</style>' not in t:
        return 'NO </style>'
    t = t.replace('</style>', CSS + '\n</style>', 1)

    # 2) Inject filter HTML after perf-metric-ctrl div block
    m = re.search(r'<div class="seg-ctrl" id="perf-metric-ctrl">.*?</div>', t, re.S)
    if not m: return 'NO perf-metric-ctrl'
    t = t.replace(m.group(0), m.group(0) + FILTER_HTML, 1)

    # 3) Inject JS state + filter logic
    # Find function renderPerf body start
    rp_match = re.search(r'(function renderPerf\(\)\{)', t)
    if not rp_match: return 'NO renderPerf'
    rp_start = rp_match.end()
    # Find first occurrence of `prods` declaration or assignment after start
    # We inject AFTER the prods declaration so we can modify it
    prods_match = re.search(r'(const prods\s*=\s*[^;]+;|let prods\s*=\s*[^;]+;)', t[rp_start:])
    if not prods_match: return 'NO prods declaration'
    prods_end = rp_start + prods_match.end()
    # Change `const prods = ...` to `let prods = ...` for mutability
    decl = prods_match.group(1)
    if decl.startswith('const'):
        new_decl = 'let' + decl[5:]
        t = t[:rp_start + prods_match.start()] + new_decl + t[rp_start + prods_match.end():]
        prods_end = rp_start + prods_match.start() + len(new_decl)

    # Now find where periodKeys is set (after this we can inject filter logic)
    # periodKeys is computed in renderPerf, we want filter AFTER periodKeys is ready
    pk_end_match = re.search(r'(periodKeys=\(periodKeys\|\|\[\]\)\.filter\(Boolean\);)', t[prods_end:])
    if not pk_end_match:
        # Fallback: inject before `const lastPK = periodKeys[periodKeys.length-1];`
        pk_end_match = re.search(r'(const lastPK\s*=\s*periodKeys\[periodKeys\.length-1\];)', t[prods_end:])
        if not pk_end_match: return 'NO periodKeys/lastPK anchor'
        inject_at = prods_end + pk_end_match.start()
    else:
        inject_at = prods_end + pk_end_match.end()
    t = t[:inject_at] + '\n' + JS_FILTER_LOGIC + t[inject_at:]

    # 4) Inject state init + wiring at end of body (before </body>)
    if '</body>' in t:
        wiring_block = '\n<script>\n' + JS_STATE + JS_WIRING + '\n</script>\n'
        t = t.replace('</body>', wiring_block + '</body>', 1)

    path.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file(): print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
