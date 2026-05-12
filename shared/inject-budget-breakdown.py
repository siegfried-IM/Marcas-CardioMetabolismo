"""Agregar tabla resumen 'Por Familia' debajo del banner explicativo en la
seccion Venta Interna vs Presupuesto, mostrando para cada familia:
  Familia · Budget · Real · Cumpl% · Pendiente · Próximo+ (redistribuido al
  primer mes del trimestre siguiente).

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

# 1) HTML container debajo del banner explicativo
ANCHOR_HTML = '<p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">% Cumplimiento mensual</p>'

# 2) JS injection: extender renderBudget para tambien computar breakdown
JS_BREAKDOWN = r"""// ── Breakdown por familia (todos los SIE products del año) ──
  (function(){
    const host = document.getElementById('bud-breakdown');
    if(!host) return;
    const _MES = (typeof MESES!=='undefined' && MESES.length===12) ? MESES : ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
    const fmtU = n=>Number(n||0).toLocaleString('es-AR');
    // 2026 fallback: derive real from IQVIA mol_perf si la funcion existe
    const getIqv = (typeof getIQVIAReal2026==='function') ? getIQVIAReal2026 : null;
    const rows = [];
    Object.keys(D.budget||{}).forEach(famKey=>{
      const fy = (D.budget[famKey]||{})[bYear];
      if(!fy) return;
      const fBud = fy.budget||[];
      let fReal = fy.real||[];
      if(bYear==='2026' && !fReal.some(v=>v!=null) && getIqv){
        const ar = getIqv(famKey); if(ar) fReal = ar;
      }
      let tB=0, tR=0, tShortPast=0, firstPending=-1;
      for(let i=0;i<12;i++){
        const b = +fBud[i]||0, r = fReal[i];
        tB += b;
        if(r!=null){ tR += +r||0; if(b>0) tShortPast += Math.max(0, b-(+r||0)); }
        else if(firstPending<0 && b>0) firstPending=i;
      }
      if(tB<=0) return; // sin budget no tiene sentido
      const triIdx = [];
      if(firstPending>=0){
        for(let i=firstPending;i<12 && triIdx.length<3;i++){
          if((+fBud[i]||0)>0) triIdx.push(i);
        }
      }
      let extra = 0;
      if(triIdx.length>0 && tShortPast>0) extra = tShortPast/triIdx.length;
      const pct = tB>0 ? Math.round(tR/tB*100) : null;
      const pend = Math.max(0, tB-tR);
      rows.push({fam:famKey, bud:tB, real:tR, pct, pend, extra, nextMes:triIdx.length?_MES[triIdx[0]]:null});
    });
    // Sort: peor cumplimiento primero (rojo arriba)
    rows.sort((a,b)=>{ const av = a.pct==null?999:a.pct; const bv=b.pct==null?999:b.pct; return av-bv; });
    const pctColor = p=>p==null?'#4b5563':p>=100?'#15803d':p>=85?'#ca8a04':'#b01e1e';
    const head = '<thead><tr>'
      + '<th style="text-align:left;padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;">Familia</th>'
      + '<th style="text-align:right;padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;">Budget</th>'
      + '<th style="text-align:right;padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;">Real</th>'
      + '<th style="text-align:right;padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;">Cumpl.</th>'
      + '<th style="text-align:right;padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;">Pendiente</th>'
      + '<th style="text-align:right;padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;">Próximo +</th>'
      + '</tr></thead>';
    const body = '<tbody>' + rows.map(r=>{
      const isCur = r.fam===bProd;
      const bg = isCur ? 'background:#fef2f2;' : '';
      const triText = (r.extra>0 && r.nextMes) ? '+'+fmtU(Math.round(r.extra))+' u. ('+r.nextMes+')' : '—';
      return '<tr style="border-top:1px solid #f3f4f6;'+bg+'cursor:pointer;" onclick="setBP(\''+r.fam.replace(/\'/g,"\\\\'")+'\')">'
        + '<td style="padding:6px 8px;font-size:11px;font-weight:'+(isCur?'700':'500')+';color:#111827;">'+r.fam+(isCur?' •':'')+'</td>'
        + '<td style="padding:6px 8px;font-size:11px;text-align:right;font-family:IBM Plex Mono,monospace;">'+fmtU(r.bud)+'</td>'
        + '<td style="padding:6px 8px;font-size:11px;text-align:right;font-family:IBM Plex Mono,monospace;">'+fmtU(r.real)+'</td>'
        + '<td style="padding:6px 8px;font-size:11px;text-align:right;font-family:IBM Plex Mono,monospace;font-weight:700;color:'+pctColor(r.pct)+';">'+(r.pct==null?'—':r.pct+'%')+'</td>'
        + '<td style="padding:6px 8px;font-size:11px;text-align:right;font-family:IBM Plex Mono,monospace;color:'+(r.pend>0?'#b01e1e':'#9ca3af')+';">'+(r.pend>0?fmtU(r.pend):'—')+'</td>'
        + '<td style="padding:6px 8px;font-size:11px;text-align:right;font-family:IBM Plex Mono,monospace;color:#92400e;">'+triText+'</td>'
        + '</tr>';
    }).join('') + '</tbody>';
    host.innerHTML = '<p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin:14px 0 8px;">Apertura por familia · Año '+bYear+'</p>'
      + '<div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff;">'
      + '<table style="width:100%;border-collapse:collapse;">' + head + body + '</table>'
      + '</div>';
  })();
  """

ANCHOR_JS = "window.__sfBudgetTotals = {budget:__sfBudget"


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if 'bud-breakdown' in t:
        return 'SKIP already'
    # 1) Insertar container HTML antes del banner explicativo:
    # busco </div> de cierre de la card y meto antes
    # Mejor: insertar al final del .card que contiene el chart.
    # Anchor: el banner explicativo termina con un </div> cerrando el bud-cap.
    # Insertamos un nuevo div justo despues del cierre de bud-cap.
    # Pattern: </div></div></div> al cierre de la card budget
    # Mas simple: insertar despues del bud-cap div container line.
    # bud-cap es: <div class="bud-cap" ...>...</div>
    if 'class="bud-cap"' not in t:
        return 'NO bud-cap'
    # find the </div> after the bud-cap explanation paragraph
    pat = re.compile(r'(El total anual de Budget se mantiene constante\.</div></div>)', re.S)
    if not pat.search(t):
        return 'NO bud-cap end pat'
    t = pat.sub(r'\1<div id="bud-breakdown" style="margin-top:14px;"></div>', t, count=1)
    # 2) Inyectar JS breakdown justo despues de window.__sfBudgetTotals = ...
    full_anchor = re.search(r'(window\.__sfBudgetTotals = \{[^}]+\};)', t)
    if not full_anchor:
        return 'NO anchor JS'
    t = t.replace(full_anchor.group(1), full_anchor.group(1) + '\n  ' + JS_BREAKDOWN, 1)
    path.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file(): print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
