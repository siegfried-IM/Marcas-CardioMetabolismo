"""Actualiza mujer/DDD/data.js (OTC_DATA.dddGineco) usando competidores-data.js.

Estrategia:
- Solo actualiza molecule.all.{regionsByMonth, productsByMonth, latestMonth, monthly}
  para las familias mapeadas. Deja etico/popular y ATC sin tocar (competidores no
  separa canal etico/popular).
- Actualiza dddGineco.months con los meses de competidores (24 meses).
- Familias sin match en competidores (SOLO liquidos, SOLO gotas, BASE) quedan
  intactas.

Mapping famName -> competidores market:
  SIN ESTROGENO       -> Isis Free (Progestagenos Solos)
  ALTA DOSIS          -> Isis
  BAJA DOSIS 21+7     -> Isis Mini
  BAJA DOSIS 24       -> Isis Mini 24
  COMPLEX             -> Siderblut Compuestos
  SOLO (solidos)      -> Siderblut Familia
  SOLO (IM)           -> Siderblut IM
  D3                  -> Trip D3
  DELTROX             -> Deltrox
"""
from __future__ import annotations
import re, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_FILE = REPO / 'mujer' / 'DDD' / 'data.js'
COMP_FILE = REPO / 'mujer' / 'DDD' / 'competidores-data.js'

# Mapping by family key in dddGineco.families
FAMILY_MAP = {
    'SIN ESTROGENO':     'Isis Free (Progestágenos Solos)',
    'ALTA DOSIS':        'Isis',
    'BAJA DOSIS 21+7':   'Isis Mini',
    'BAJA DOSIS 24':     'Isis Mini 24',
    'COMPLEX':           'Siderblut Compuestos',
    'SOLO (sólidos)':       'Siderblut Familia',
    'SOLO (IM)':         'Siderblut IM',
    'D3':                'Trip D3',
    'DELTROX':           'Deltrox',
}


def load_comp():
    s = COMP_FILE.read_text(encoding='utf-8').replace('window.SFG_COMP_DATA = ', '').rstrip(';\n')
    return json.loads(s)


def build_variant_from_comp(comp_data, mk_name):
    """Build {months, regionsByMonth, productsByMonth, latestMonth} from a competidores market."""
    months = comp_data.get('months', [])
    regions = comp_data.get('regions', [])
    mk_obj = comp_data.get('markets', {}).get(mk_name)
    if not mk_obj:
        return None

    bm = mk_obj.get('brand_monthly', {})
    tm = mk_obj.get('total_monthly', {})
    sie_set = set(s.upper() for s in mk_obj.get('brands', []))

    regions_by_month = {}
    products_by_month = {}

    for mi, mk in enumerate(months):
        # regionsByMonth
        rrows = []
        for reg in regions:
            if reg == '-' or reg.startswith('__'):
                continue
            tot_arr = tm.get(reg, [])
            total = (tot_arr[mi] if mi < len(tot_arr) else 0) or 0
            sie = 0
            for brand, regs in bm.items():
                if brand.upper() not in sie_set:
                    continue
                arr = regs.get(reg, [])
                sie += (arr[mi] if mi < len(arr) else 0) or 0
            if total > 0:
                share = round(sie / total * 100, 1)
                rrows.append({'name': reg, 'total': total, 'sie': sie, 'share': share})
        rrows.sort(key=lambda x: -x['total'])
        regions_by_month[mk] = rrows

        # productsByMonth
        brand_units = {}
        total_market_month = 0
        for brand, regs in bm.items():
            u = 0
            for arr in regs.values():
                u += (arr[mi] if mi < len(arr) else 0) or 0
            brand_units[brand] = u
            total_market_month += u
        prows = []
        for brand, u in brand_units.items():
            if u <= 0:
                continue
            share = round(u / total_market_month * 100, 1) if total_market_month > 0 else 0
            prows.append({
                'product': brand,
                'units': u,
                'share': share,
                'isSie': brand.upper() in sie_set,
            })
        prows.sort(key=lambda x: -x['units'])
        products_by_month[mk] = prows

    return {
        'months': months,
        'regionsByMonth': regions_by_month,
        'productsByMonth': products_by_month,
        'latestMonth': months[-1] if months else '',
    }


def main():
    comp = load_comp()
    comp_months = comp.get('months', [])

    t = DATA_FILE.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DATA\s*=\s*', t)
    if not m:
        print('  ERROR: no OTC_DATA in mujer/DDD/data.js')
        return
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    prefix = t[:ob]
    suffix = t[ob + end:]

    dg = D.setdefault('dddGineco', {})
    # Update top-level months
    dg['months'] = list(comp_months)

    fams = dg.setdefault('families', {})
    updated = []
    skipped_no_market = []

    for fam_key, comp_mk in FAMILY_MAP.items():
        if fam_key not in fams:
            skipped_no_market.append((fam_key, 'family-missing'))
            continue
        built = build_variant_from_comp(comp, comp_mk)
        if not built:
            skipped_no_market.append((fam_key, f'market-missing:{comp_mk}'))
            continue
        mol = fams[fam_key].setdefault('molecule', {})
        all_v = mol.setdefault('all', {})
        # Preserve existing keys we don't overwrite (family, monthly)
        all_v['family'] = fam_key
        all_v['latestMonth'] = built['latestMonth']
        all_v.setdefault('monthly', {})
        all_v['regionsByMonth'] = built['regionsByMonth']
        all_v['productsByMonth'] = built['productsByMonth']
        updated.append(fam_key)

    DATA_FILE.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                         encoding='utf-8', newline='')

    print(f'  mujer: OK [months={len(comp_months)}, families_updated={len(updated)}]')
    print(f'    updated: {updated}')
    if skipped_no_market:
        print(f'    skipped: {skipped_no_market}')
    # Inform user about unmapped families
    unmapped = [k for k in fams.keys()
                if k not in FAMILY_MAP and not re.match(r'^[A-Z]\d', k)]
    if unmapped:
        print(f'    unmapped (left intact): {unmapped}')


if __name__ == '__main__':
    main()
