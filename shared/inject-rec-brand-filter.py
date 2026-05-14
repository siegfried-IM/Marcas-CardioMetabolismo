"""Agrega filtro de competidores al panel de Recetas (rec-comp-panel)
en cada dashboard. Mismo UX que el filtro de Mercado IQVIA.

Aplica a las 7 lineas. Idempotente."""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# HTML del filtro a insertar DENTRO del rec-comp-panel, ANTES del rec-comp-table
FILTER_HTML = '''
        <div class="perf-bf" id="rec-bf">
          <span class="lbl">Comparar con</span>
          <div class="seg" id="rcf-mode">
            <button data-m="top5">Top 5</button>
            <button data-m="top10" class="on">Top 10</button>
            <button data-m="sie">Solo SIE</button>
            <button data-m="all">Todos</button>
          </div>
          <input type="text" class="search" id="rcf-search" placeholder="Buscar marca..." />
          <div class="pills" id="rcf-pills"></div>
        </div>'''

JS_WIRING = '''
// Wire rec brand filter
(function(){
  if(window.__sfRecPFWired) return;
  window.__sfRecPFWired = true;
  window.__sfRecPF = window.__sfRecPF || { mode:'top10', selected:new Set(), search:'' };
  const ready = function(fn){
    if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  };
  ready(function(){
    const seg = document.getElementById('rcf-mode');
    const search = document.getElementById('rcf-search');
    const pills = document.getElementById('rcf-pills');
    if(seg) seg.addEventListener('click', function(e){
      const b = e.target.closest('button[data-m]');
      if(!b) return;
      seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      window.__sfRecPF.mode = b.dataset.m;
      window.__sfRecPF.selected = new Set();
      if(typeof renderRec==='function') renderRec();
    });
    if(search) search.addEventListener('input', function(e){
      window.__sfRecPF.search = e.target.value;
      if(typeof renderRec==='function') renderRec();
    });
    if(pills) pills.addEventListener('click', function(e){
      const p = e.target.closest('.pill[data-prod]');
      if(!p) return;
      const prod = p.dataset.prod;
      if(window.__sfRecPF.selected.has(prod)) window.__sfRecPF.selected.delete(prod);
      else window.__sfRecPF.selected.add(prod);
      if(typeof renderRec==='function') renderRec();
    });
  });
})();
'''

# JS logic to inject inside renderRecComp after const sorted=...
FILTER_LOGIC = '''
  // Apply brand filter to sorted list
  if(!window.__sfRecPF) window.__sfRecPF = { mode:'top10', selected:new Set(), search:'' };
  const _pf = window.__sfRecPF;
  const _allSorted = sorted.slice();
  let _filteredSorted = _allSorted;
  if(_pf.mode==='top5') _filteredSorted = _allSorted.slice(0,5);
  else if(_pf.mode==='top10') _filteredSorted = _allSorted.slice(0,10);
  else if(_pf.mode==='sie') _filteredSorted = _allSorted.filter(([p,d])=>p.includes(' SIE'));
  if(_pf.selected.size > 0){
    _filteredSorted = _allSorted.filter(([p,d])=>_pf.selected.has(p));
  }
  // Always include SIE
  _allSorted.filter(([p,d])=>p.includes(' SIE')).forEach(s=>{
    if(!_filteredSorted.find(x=>x[0]===s[0])) _filteredSorted.push(s);
  });
  // Render pills (from full sorted list)
  const _pillEl = document.getElementById('rcf-pills');
  if(_pillEl){
    const _shown = new Set(_filteredSorted.map(([p])=>p));
    const q = (_pf.search||'').toLowerCase();
    const _pillList = q ? _allSorted.filter(([p])=>p.toLowerCase().includes(q)) : _allSorted.slice(0,30);
    _pillEl.innerHTML = _pillList.map(([p])=>{
      const on = _shown.has(p);
      const sie = p.includes(' SIE')?' sie':'';
      return `<span class="pill${on?' on':''}${sie}" data-prod="${p.replace(/"/g,'&quot;')}">${p}</span>`;
    }).join('');
  }
  sorted = _filteredSorted;
'''


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if 'rec-bf' in t and '__sfRecPF' in t:
        return 'SKIP already'

    # 1) Insert filter HTML inside rec-comp-panel, before rec-comp-table
    anchor = '<div id="rec-comp-table"></div>'
    if anchor not in t:
        return 'NO rec-comp-table anchor'
    t = t.replace(anchor, FILTER_HTML + '\n        ' + anchor, 1)

    # 2) Inject filter logic inside renderRecComp after `const sorted=...`
    m = re.search(r'(function renderRecComp\(.*?\)\{)', t, re.S)
    if not m: return 'NO renderRecComp'
    rc_start = m.end()
    sorted_m = re.search(r'(const sorted=[^;]+;)', t[rc_start:])
    if not sorted_m: return 'NO sorted decl'
    sorted_end = rc_start + sorted_m.end()
    # Change const sorted -> let sorted for mutability
    t = t[:rc_start + sorted_m.start()] + 'let sorted' + t[rc_start + sorted_m.start()+'const sorted'.__len__():]
    # Now inject filter logic after the sorted decl
    sorted_end = rc_start + sorted_m.end()  # same offset since 'const'->'let' is same length
    t = t[:sorted_end] + '\n' + FILTER_LOGIC + t[sorted_end:]

    # 3) Inject wiring before </body> if not present
    if '__sfRecPFWired' not in t:
        if '</body>' in t:
            t = t.replace('</body>', '<script>\n' + JS_WIRING + '\n</script>\n</body>', 1)

    path.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file(): print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
