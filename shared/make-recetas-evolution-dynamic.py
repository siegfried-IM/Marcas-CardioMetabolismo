"""Hace dinamica la tabla 'SIE · Evolucion mensual' de Recetas en las 7 lineas.

Comparacion: ultimo mes disponible vs mismo mes del anio anterior (+ 2 anios
atras como contexto). Los labels y deltas se calculan en runtime, no hardcoded.

Tabla resultante (3 cols + delta YoY):
  Metrica | {prev2YrMo} | {prevYrMo} | {lastMo} | Δ {prevYr}→{lastYr}
  Recetas | data[m-24].recetas | data[m-12].recetas | data[m].recetas | %
  MS%     | msD[m-24]          | msD[m-12]          | msD[m]          | pp

NO toca la tabla 'SIE vs Mercado · Total Anual' (anios fijos 2024/2025).
NO toca seg-ctrl, charts, ni otras secciones.
Idempotente: si ya esta dinamico, no hace nada.
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
    'mujer/index.html',
]

NEW_BLOCK = """  const keys2=sortM(Object.keys(data));
  const lastMes=keys2[keys2.length-1]||null;
  const prevYearMes=lastMes?(()=>{const[m,y]=lastMes.split(' ');return `${m} ${parseInt(y,10)-1}`;})():null;
  const prev2YearMes=lastMes?(()=>{const[m,y]=lastMes.split(' ');return `${m} ${parseInt(y,10)-2}`;})():null;
  const lastData=lastMes?(data[lastMes]||{}):{};
  const prevData=prevYearMes?(data[prevYearMes]||{}):{};
  const prev2Data=prev2YearMes?(data[prev2YearMes]||{}):{};
  const msObj=D.rec_ms?.[rProd]||{};const msD=msObj.ms||{};
  const msLast=lastMes?msD[lastMes]:null;
  const msPrev=prevYearMes?msD[prevYearMes]:null;
  const msPrev2=prev2YearMes?msD[prev2YearMes]:null;
  const recDelta=(lastData.recetas&&prevData.recetas)?Math.round((lastData.recetas/prevData.recetas-1)*100):null;
  const msDelta=(msLast!=null&&msPrev!=null)?+(msLast-msPrev).toFixed(2):null;
  const _monthEs={Jan:'Ene',Feb:'Feb',Mar:'Mar',Apr:'Abr',May:'May',Jun:'Jun',Jul:'Jul',Aug:'Ago',Sep:'Sep',Oct:'Oct',Nov:'Nov',Dec:'Dic'};
  const _fmtMo=lbl=>{if(!lbl)return '—';const[mon,year]=lbl.split(' ');return `${_monthEs[mon]||mon} ${year.slice(-2)}`;};
  const prev2Lbl=_fmtMo(prev2YearMes);
  const prevLbl=_fmtMo(prevYearMes);
  const lastLbl=_fmtMo(lastMes);
  const deltaLbl=(prevYearMes&&lastMes)?`Δ ${prevYearMes.split(' ')[1].slice(-2)}→${lastMes.split(' ')[1].slice(-2)}`:'Δ YoY';
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
  const sieT24=_sieYearTot('2024'), sieT25=_sieYearTot('2025');
  const mktT24=_mktYearTot('2024'), mktT25=_mktYearTot('2025');
  const sieDY=sieT24&&sieT25?Math.round((sieT25/sieT24-1)*100):null;
  const mktDY=mktT24&&mktT25?Math.round((mktT25/mktT24-1)*100):null;
  const _fmtN = v => v==null ? '—' : (typeof v==='number' ? v.toLocaleString('es-AR') : v);
  const _pctCls = v => v==null?'#9ca3af':v>=0?'#16a34a':'#dc2626';
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
      <thead><tr>${thL('Métrica')}${th(prev2Lbl)}${th(prevLbl)}${th(lastLbl)}${th(deltaLbl)}</tr></thead>
      <tbody>
        <tr style="border-bottom:1px solid #f3f4f6;">${tdL('Recetas')}${tdN(prev2Data.recetas)}${tdN(prevData.recetas)}${tdN(lastData.recetas)}${tdD(recDelta,false)}</tr>
        <tr>${tdL('MS%')}${tdN(msPrev2!=null?msPrev2.toFixed(2)+'%':null)}${tdN(msPrev!=null?msPrev.toFixed(2)+'%':null)}${tdN(msLast!=null?msLast.toFixed(2)+'%':null)}${tdD(msDelta,true)}</tr>
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


def patch_file(path):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')

    # Find block: from `  const keys2=sortM(Object.keys(data));`
    # to `\nfunction round2(v){...}`
    start_pat = re.compile(r'  const keys2=sortM\(Object\.keys\(data\)\);')
    sm = start_pat.search(t)
    if not sm:
        return 'no-start'
    end_pat = re.compile(r'\nfunction round2\(v\)\{return Math\.round\(v\*100\)/100;\}')
    em = end_pat.search(t, sm.start())
    if not em:
        return 'no-end'

    current_block = t[sm.start():em.start()].rstrip()
    new_block = NEW_BLOCK.rstrip()
    if current_block == new_block:
        return 'already-dynamic'

    new_t = t[:sm.start()] + new_block + t[em.start():]
    p.write_text(new_t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in TARGETS:
        print(f'  {f}: {patch_file(f)}')


if __name__ == '__main__':
    main()
