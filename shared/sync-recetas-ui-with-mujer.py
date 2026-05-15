"""Sincroniza la seccion Recetas de cardio/ATB/OTC/respiratorio/SNC/dermato con
la version de mujer (linea fuente).

Cambios:
1. seg-ctrl (toggles): deja solo 'Recetas' + 'MS%' (saca 'Trimestral' y 'Medicos')
2. rec-detail (panel derecho de renderRec): reemplaza el bloque 'Comparativo'
   sabana por dos tablas (SIE Evolucion mensual + SIE vs Mercado Total Anual)
   identicas a mujer.

Idempotente: si ya esta sincronizado, no hace nada.
NO toca otras secciones, charts ni datos.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGETS = [
    'cardio/index.html',
    'ATB/index.html',
    'OTC/index.html',
    'respiratorio/index.html',
    'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# === Templates extraidos de mujer/index.html ===

MUJER_SEG_CTRL = '''<div class="seg-ctrl" id="rec-view-ctrl">
            <button class="seg on" data-v="rec">Recetas</button>
            <button class="seg" data-v="ms">MS%</button>
          </div>'''

MUJER_DETAIL_BLOCK = """  const keys2=sortM(Object.keys(data));
  const j24=data['Jan 2024']||{},j25=data['Jan 2025']||{},d25=data['Dec 2025']||{};
  const r2425=j24.recetas&&j25.recetas?Math.round((j25.recetas/j24.recetas-1)*100):null;
  const m2425=j24.medicos&&j25.medicos?Math.round((j25.medicos/j24.medicos-1)*100):null;
  const msObj=D.rec_ms?.[rProd]||{};const msD=msObj.ms||{};
  const msLast=msD['Dec 2025'];const msFirst=msD['Jan 2024'];
  const msDelta=msLast&&msFirst?((msLast/msFirst-1)*100).toFixed(1):null;
  // Totales por anio (SIE y Mercado) a partir de D.recetas y D.rec_comp
  const _compData=D.rec_comp?.[rProd]||{};
  function _sieYearTot(y){
    let s=0;
    Object.entries(data).forEach(([k,v])=>{if(k.endsWith(' '+y))s+=(v.recetas||0);});
    return s||null;
  }
  function _mktYearTot(y){
    let s=0;
    Object.values(_compData).forEach(p=>{
      Object.entries(p.monthly||{}).forEach(([k,v])=>{if(k.endsWith(' '+y))s+=(v||0);});
    });
    return s||null;
  }
  function _mktMonth(k){
    let s=0;Object.values(_compData).forEach(p=>{s+=(p.monthly?.[k]||0);});
    return s||null;
  }
  const sieT24=_sieYearTot('2024'), sieT25=_sieYearTot('2025');
  const mktT24=_mktYearTot('2024'), mktT25=_mktYearTot('2025');
  const sieDY=sieT24&&sieT25?Math.round((sieT25/sieT24-1)*100):null;
  const mktDY=mktT24&&mktT25?Math.round((mktT25/mktT24-1)*100):null;
  const mkt_j25=_mktMonth('Jan 2025'), mkt_d25=_mktMonth('Dec 2025');
  // Comparativo true side-by-side (no sabana)
  const _fmtN = v => v==null ? '—' : (typeof v==='number' ? v.toLocaleString('es-AR') : v);
  const _fmtP = v => v==null ? '—' : (typeof v==='number' ? (v>=0?'+':'')+v+'%' : v);
  const _pctCls = v => v==null?'#9ca3af':v>=0?'#16a34a':'#dc2626';
  const _yoyRec = (j24.recetas&&d25.recetas) ? Math.round((d25.recetas/j24.recetas-1)*100) : null;
  const _yoyMed = (j25.medicos&&d25.medicos) ? Math.round((d25.medicos/j25.medicos-1)*100) : null;
  const _yoyMS  = (msFirst&&msLast) ? +(msLast-msFirst).toFixed(2) : null;
  // Render tables
  const th = (txt) => `<th style="text-align:right;padding:6px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid #e5e7eb;">${txt}</th>`;
  const thL = (txt) => `<th style="text-align:left;padding:6px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid #e5e7eb;">${txt}</th>`;
  const tdN = (v) => `<td style="padding:6px 8px;text-align:right;font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;color:#111827;">${_fmtN(v)}</td>`;
  const tdL = (v) => `<td style="padding:6px 8px;text-align:left;font-size:11px;color:#4b5563;">${v}</td>`;
  const tdD = (v, isPP) => {
    if(v==null) return `<td style="padding:6px 8px;text-align:right;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#9ca3af;">—</td>`;
    const txt = isPP ? (v>=0?'+':'')+v.toFixed(2)+' pp' : (v>=0?'+':'')+v+'%';
    return `<td style="padding:6px 8px;text-align:right;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;color:${_pctCls(v)};">${txt}</td>`;
  };
  document.getElementById('rec-detail').innerHTML = `
    <p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">SIE · Evolución mensual</p>
    <table style="width:100%;border-collapse:collapse;margin-bottom:14px;">
      <thead><tr>${thL('Métrica')}${th('Ene 24')}${th('Ene 25')}${th('Dic 25')}${th('Δ 24→25')}</tr></thead>
      <tbody>
        <tr style="border-bottom:1px solid #f3f4f6;">${tdL('Recetas')}${tdN(j24.recetas)}${tdN(j25.recetas)}${tdN(d25.recetas)}${tdD(_yoyRec,false)}</tr>
        <tr>${tdL('MS%')}${tdN(msFirst?msFirst.toFixed(2)+'%':null)}${tdN(msD['Jan 2025']?msD['Jan 2025'].toFixed(2)+'%':null)}${tdN(msLast?msLast.toFixed(2)+'%':null)}${tdD(_yoyMS,true)}</tr>
      </tbody>
    </table>
    <p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">SIE vs Mercado · Total Anual</p>
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr>${thL('')}${th('2024')}${th('2025')}${th('Δ YoY')}</tr></thead>
      <tbody>
        <tr style="border-bottom:1px solid #f3f4f6;">${tdL('SIE')}${tdN(sieT24)}${tdN(sieT25)}${tdD(sieDY,false)}</tr>
        <tr>${tdL('Mercado')}${tdN(mktT24)}${tdN(mktT25)}${tdD(mktDY,false)}</tr>
      </tbody>
    </table>`;
}"""


def patch_seg_ctrl(t):
    """Reduce seg-ctrl to Recetas + MS% (saca Trimestral y Medicos)."""
    # Match the entire seg-ctrl div with all its children
    pat = re.compile(
        r'<div class="seg-ctrl" id="rec-view-ctrl">'
        r'(.*?)'
        r'</div>',
        re.DOTALL
    )
    m = pat.search(t)
    if not m:
        return t, False
    current = m.group(0)
    if current.strip() == MUJER_SEG_CTRL.strip():
        return t, False  # idempotent
    return t[:m.start()] + MUJER_SEG_CTRL + t[m.end():], True


def patch_detail_block(t):
    """Reemplaza el bloque rec-detail desde `const keys2=sortM(...)` hasta el
    `;` final + `}` que cierra renderRec, antes de `function round2`."""
    # The block: starts with "  const keys2=sortM(Object.keys(data));"
    # ends with "    </table>`;\n}" (last template literal of innerHTML, then }
    # which closes renderRec).
    # We'll locate by the surrounding markers.
    start_pat = re.compile(r'  const keys2=sortM\(Object\.keys\(data\)\);')
    sm = start_pat.search(t)
    if not sm:
        return t, False, 'no-start'

    # End: find `function round2(v){return Math.round(v*100)/100;}` after sm.start()
    end_pat = re.compile(r'\nfunction round2\(v\)\{return Math\.round\(v\*100\)/100;\}')
    em = end_pat.search(t, sm.start())
    if not em:
        return t, False, 'no-end'

    # The block ends right before `\nfunction round2`. The closing brace `}` of
    # renderRec is the last char before that newline (or it's at em.start() - 1).
    # Our MUJER_DETAIL_BLOCK ends with `}` (closing renderRec).
    current_block = t[sm.start():em.start()].rstrip()
    new_block = MUJER_DETAIL_BLOCK.rstrip()
    if current_block == new_block:
        return t, False, 'already-synced'

    return t[:sm.start()] + new_block + t[em.start():], True, 'ok'


def patch_file(path):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')

    t2, seg_changed = patch_seg_ctrl(t)
    t3, det_changed, status = patch_detail_block(t2)

    if not seg_changed and not det_changed:
        return 'already-synced'

    p.write_text(t3, encoding='utf-8', newline='')
    parts = []
    if seg_changed: parts.append('seg-ctrl')
    if det_changed: parts.append(f'rec-detail({status})')
    return 'OK: ' + ', '.join(parts)


def main():
    for f in TARGETS:
        print(f'  {f}: {patch_file(f)}')


if __name__ == '__main__':
    main()
