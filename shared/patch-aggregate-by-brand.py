"""Aplica el agregado por marca al renderPerf de cada linea (cardio, ATB, OTC,
respi, SNC, dermato). Mujer ya lo tiene desde commit 2fb65a7.

Antes: cada presentacion (e.g. 'ACEMUK 200MG x 10') aparece como fila separada,
con su propio IE distinto al del KPI strip arriba.

Despues: una sola fila 'ACEMUK' que suma todas las presentaciones,
consistente con el strip y brandKpis.

Idempotente."""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

AGGREGATE_JS = r"""// Extract brand name from product presentation
function _extractBrand(prod){
  if(!prod) return prod;
  const STOP = new Set(['TABL','TABLET','TABLETA','TABLETAS','CAP','CAPS','CAPSULA','CAPSULAS',
    'COMP','COMPR','COMPS','COMPRIMIDO','COMPRIMIDOS','AMP','AMPOLLA','AMPOLLAS','JBE','JARABE',
    'INY','INYECTABLE','SUSP','SUSPENSION','POL','POLVO','SOB','SOBRE','SOBRES','GTAS','GOTAS',
    'SOL','SOLUC','SOLUCION','CR','CREMA','UNG','UNGUENTO','GEL','EMUL','LOC','LOCION',
    'PARCHE','OVUL','OVULO','OVULOS','IMPL','IMPLANTE','ANILLO','ANILLOS','S/ESTROG','SE',
    'EFER','EFERV','RECUB','RECUBIE','REC','GRAG','GRAGEAS','MAST','MASTIC','LIQ','LIQUIDO',
    'AERO','AEROSOL','INHAL','INHALACION','SPRAY','COLIRIO','GINEC','VAGINAL','PESARIO',
    'OFT','BOLS','BOLSA','PVO','PLV','MG','ML','G','MCG','UI','PCT','CHEW']);
  const toks = String(prod).trim().split(/\s+/);
  const out = [];
  for(const t of toks){
    const u = t.toUpperCase().replace(/[.,;:()/\\-]/g,'');
    if(STOP.has(u)) break;
    if(/^[\d]/.test(u)) break;
    out.push(t);
  }
  return out.length ? out.join(' ') : toks[0];
}
function _aggregateByBrand(rawProds){
  const groups = new Map();
  rawProds.forEach(p=>{
    const brand = _extractBrand(p.prod);
    let agg = groups.get(brand);
    if(!agg){
      agg = {prod:brand, is_sie:false, monthly_vals:{}, ytd:{}, mat:{}, quarterly_vals:{},
             ms_monthly:{}, ms_ytd:{}, ms_mat:{}, ms_quarterly:{}, _isAgg:true};
      groups.set(brand, agg);
    }
    if(p.is_sie) agg.is_sie = true;
    ['monthly_vals','ytd','mat','quarterly_vals'].forEach(f=>{
      Object.entries(p[f]||{}).forEach(([k,v])=>{
        if(v!=null) agg[f][k] = (agg[f][k]||0) + (+v||0);
      });
    });
  });
  const brands = [...groups.values()];
  ['monthly_vals','ytd','mat','quarterly_vals'].forEach((f,idx)=>{
    const msField = ['ms_monthly','ms_ytd','ms_mat','ms_quarterly'][idx];
    const allKeys = new Set();
    brands.forEach(b=>Object.keys(b[f]).forEach(k=>allKeys.add(k)));
    allKeys.forEach(k=>{
      let totalMkt = 0;
      brands.forEach(b=>{ totalMkt += (+b[f][k]||0); });
      if(totalMkt>0){
        brands.forEach(b=>{
          const v = +b[f][k]||0;
          b[msField][k] = (v/totalMkt)*100;
        });
      }
    });
  });
  return brands;
}

"""


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if '_aggregateByBrand' in t:
        return 'SKIP already'
    # Find: function renderPerf(){
    m = re.search(r'(function renderPerf\(\)\{)', t)
    if not m:
        return 'NO renderPerf'
    # Insert helper functions BEFORE renderPerf
    insertion_point = m.start()
    t = t[:insertion_point] + AGGREGATE_JS + t[insertion_point:]
    # Now replace `const prods=...products` with aggregated version
    if 'const prods=molData.products' in t:
        t = t.replace('const prods=molData.products', 'const prods=_aggregateByBrand(molData.products)', 1)
    elif 'const prods = molData.products' in t:
        t = t.replace('const prods = molData.products', 'const prods = _aggregateByBrand(molData.products)', 1)
    elif 'const prods=buildPerfProducts(pMol);' in t:
        t = t.replace('const prods=buildPerfProducts(pMol);',
                      'const prods=_aggregateByBrand(buildPerfProducts(pMol));', 1)
    else:
        return 'NO prods assignment'
    path.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
