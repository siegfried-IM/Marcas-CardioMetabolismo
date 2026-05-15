"""Actualiza DDD/index.html (o equivalente) usando los datos de
competidores-data.js (Shape A, 24 meses Apr 2024 - Mar 2026).

Para cada DDD page por linea:
  D.months       <- competidores months (24)
  D.regions      <- mismas 42 regiones
  D.markets[mk].brand_monthly  <- del comp data, agregando __NAC__ (sum regiones)
  D.markets[mk].total_monthly  <- del comp data + __NAC__
  D.markets[mk].brands         <- SIE list del comp data
  D.markets[mk].total_units    <- recomputed sum
  D.markets[mk].sie_units      <- recomputed sum (todas SIE)
  D.markets[mk].global_ms      <- recomputed sie/total*100

Preserva los otros campos (clase, brand_meta, top_brands, region_data) sin tocar.
"""
from __future__ import annotations
import re, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (DDD html path, competidores-data.js path) por linea
LINES = [
    ('cardio/DDD/index.html',       'cardio/DDD/competidores-data.js'),
    ('ATB/DDD/index.html',          'ATB/DDD/competidores-data.js'),
    ('OTC/DDD/index.html',          'OTC/DDD/competidores-data.js'),
    ('respiratorio/DDD/index.html', 'respiratorio/DDD/competidores-data.js'),
    ('mujer/DDD/index.html',        'mujer/DDD/competidores-data.js'),
    ('SNC/DDD/psq_ddd.html',        'SNC/DDD/competidores-data.js'),
    ('dermatologia/dermato_ddd.html','dermatologia/competidores-data.js'),
]


def load_comp(path):
    s = (REPO / path).read_text(encoding='utf-8').replace('window.SFG_COMP_DATA = ', '').rstrip(';\n')
    return json.loads(s)


def load_ddd(path):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D\s*=\s*\{', t)
    if not m: return None, None, None, None, None
    ob = m.end() - 1
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    return t[:ob], D, t[ob+end:], p, m.start()


def update_market(ddd_mkt, comp_mkt, months_count):
    """Update brand_monthly, total_monthly with comp data. Recompute totals."""
    if not comp_mkt: return False
    new_brand_monthly = {}
    for brand, regions in comp_mkt.get('brand_monthly', {}).items():
        if not isinstance(regions, dict): continue
        new_entry = {}
        nac = [0] * months_count
        for reg, arr in regions.items():
            if not isinstance(arr, list): continue
            # Pad to months_count if shorter
            padded = list(arr) + [0] * max(0, months_count - len(arr))
            padded = padded[:months_count]
            new_entry[reg] = padded
            for i in range(months_count):
                v = padded[i] or 0
                nac[i] += v
        new_entry['__NAC__'] = nac
        new_brand_monthly[brand] = new_entry
    ddd_mkt['brand_monthly'] = new_brand_monthly

    new_total_monthly = {}
    total_nac = [0] * months_count
    for reg, arr in comp_mkt.get('total_monthly', {}).items():
        if not isinstance(arr, list): continue
        padded = list(arr) + [0] * max(0, months_count - len(arr))
        padded = padded[:months_count]
        new_total_monthly[reg] = padded
        for i in range(months_count):
            total_nac[i] += padded[i] or 0
    new_total_monthly['__NAC__'] = total_nac
    ddd_mkt['total_monthly'] = new_total_monthly

    # SIE brands list
    ddd_mkt['brands'] = list(comp_mkt.get('brands', []))

    # Recompute totals across all months / regions
    total_units = sum(total_nac)
    sie_units = 0
    for sie_brand in ddd_mkt['brands']:
        if sie_brand in new_brand_monthly:
            sie_units += sum(new_brand_monthly[sie_brand].get('__NAC__', []))
    ddd_mkt['total_units'] = total_units
    ddd_mkt['sie_units'] = sie_units
    ddd_mkt['global_ms'] = round(sie_units / total_units * 100, 1) if total_units > 0 else 0
    return True


def patch_line(ddd_path, comp_path):
    comp = load_comp(comp_path)
    prefix, D, suffix, file_p, _ = load_ddd(ddd_path)
    if D is None: return 'NO inline D'

    new_months = list(comp.get('months', []))
    new_regions = list(comp.get('regions', []))
    months_count = len(new_months)
    D['months'] = new_months
    D['regions'] = new_regions
    # Generate quarters from months
    quarters = []
    for mk in new_months:
        try:
            mes, yr = mk.split('-')
            mes_idx = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'].index(mes)
            q = mes_idx // 3 + 1
            qk = f'Q{q}-{yr}'
            if qk not in quarters: quarters.append(qk)
        except: continue
    D['quarters'] = quarters

    markets_updated = 0
    markets_added = 0
    for mk_name, comp_mkt in comp.get('markets', {}).items():
        if mk_name in D.get('markets', {}):
            ok = update_market(D['markets'][mk_name], comp_mkt, months_count)
            if ok: markets_updated += 1
        else:
            # Add new market with minimal structure
            new_mkt = {
                'brands': list(comp_mkt.get('brands', [])),
                'clase': '',
                'total_units': 0, 'sie_units': 0, 'global_ms': 0,
                'brand_monthly': {}, 'total_monthly': {},
                'brand_meta': {}, 'top_brands': [], 'region_data': {},
            }
            update_market(new_mkt, comp_mkt, months_count)
            D.setdefault('markets', {})[mk_name] = new_mkt
            markets_added += 1

    # Bug-fix: prefix ya termina con "const D = " porque ob apunta a '{', no
    # antes de la asignacion. Por eso NO agregamos otro "const D = ".
    file_p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                      encoding='utf-8', newline='')
    return f'OK [months={months_count}, markets_updated={markets_updated}, added={markets_added}]'


def main():
    for ddd, comp in LINES:
        try:
            print(f'  {ddd}: {patch_line(ddd, comp)}')
        except Exception as e:
            import traceback
            print(f'  {ddd}: ERROR {e}')


if __name__ == '__main__':
    main()
