#!/usr/bin/env python3
"""
shared/build-kpis.py

Construye `kpis.json` con KPIs SIE-only de cada linea para el panel
"Indicadores Clave" del hub. Lee data de cada dashboard (data.js o
inline `const D = {...}` en index.html) y para cada periodo
(YTD / Trimestre / Semestre / MAT) calcula:

  - Recetas SIE: suma de rec_ms[fam].sie por mes en la ventana del
    periodo. Solo SIE.
  - MS Recetas: ponderado = sum(sie) / sum(market) en la ventana.
    El market se obtiene de rec_ms[fam].sie / (ms/100) cuando
    ms>0; sino se asume mercado=sie (100% MS).
  - Ventas Units IQVIA SIE: suma de mol_perf[mol].products[i].monthly_vals
    por mes en la ventana, filtrando is_sie=true.
  - MS Units IQVIA: sum_sie_units / sum_market_units en la ventana.

Periodos (cierre = ultimo mes en data, normalmente Mar 2026):
  - YTD       : Ene del año del cierre .. cierre   vs  mismo rango año anterior
  - Trimestre : ultimos 3 meses                    vs  3 meses previos
  - Semestre  : ultimos 6 meses                    vs  6 meses previos
  - MAT       : ultimos 12 meses                   vs  12 meses previos

Output: kpis.json en la raiz del repo. El hub kpis.html lo fetchea.

Uso:
    py shared/build-kpis.py [--out kpis.json] [--repo .]
"""

from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

MES_EN = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
          7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
MES_INV = {v:k for k,v in MES_EN.items()}

# Definicion de lineas: como cargar la data
LINES = [
    {'key':'cardio',  'name':'CardioMetabólica', 'icon':'❤️', 'color':'#B01E1E',
     'href':'cardio/',        'owner':'Diego Fernández',
     'source':('data.js','cardio/data.js')},
    {'key':'antibio', 'name':'Antibióticos',     'icon':'🦠', 'color':'#16A34A',
     'href':'ATB/',           'owner':'Antonella Mariani',
     'source':('data.js','ATB/data.js')},
    {'key':'mujer',   'name':'Línea Mujer',      'icon':'🌸', 'color':'#DB2777',
     'href':'mujer/',         'owner':'María Hernández',
     'source':('inline','mujer/index.html')},
    {'key':'snc',     'name':'S.N.C.',           'icon':'🧠', 'color':'#7C3AED',
     'href':'SNC/',           'owner':'Juan Filidoro',
     'source':('inline','SNC/index.html')},
    {'key':'resp',    'name':'Respiratoria',     'icon':'🫁', 'color':'#0D9488',
     'href':'respiratorio/',  'owner':'Antonella Mariani',
     'source':('data.js','respiratorio/data.js')},
    {'key':'otx',     'name':'OTC',              'icon':'🩹', 'color':'#2563EB',
     'href':'OTC/',           'owner':'Antonella Mariani',
     'source':('data.js','OTC/data.js')},
]


def load_inline(html_path):
    text = Path(html_path).read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D = (\{)', text)
    if not m: return None
    obj_start = m.start() + len('const D = ')
    obj_start = text.index('{', obj_start)
    D, _ = json.JSONDecoder().raw_decode(text[obj_start:])
    return D


def load_data_js(data_js_path):
    text = Path(data_js_path).read_text(encoding='utf-8-sig', errors='replace')
    m1 = re.search(r'window\.OTC_DATA\s*=\s*', text)
    m2 = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    if not m2: return None
    obj_start2 = text.index('{', m2.end())
    d2, _ = json.JSONDecoder().raw_decode(text[obj_start2:])
    return d2


def month_key(year, month_num):
    return f'{MES_EN[month_num]} {year}'


def add_months(year, month_num, delta):
    """delta puede ser negativo. Devuelve (year, month_num) ajustado."""
    total = (year * 12 + (month_num - 1)) + delta
    y, m = divmod(total, 12)
    return y, m + 1


def month_range(end_year, end_month, n_months):
    """Devuelve los n_months month_keys terminando en end_year/end_month, ASC."""
    out = []
    for i in range(n_months - 1, -1, -1):
        y, m = add_months(end_year, end_month, -i)
        out.append(month_key(y, m))
    return out


def find_latest_month_in_data(D):
    """Busca el ultimo month_key con data en rec_ms o mol_perf.
    Devuelve (year, month_num) o None."""
    candidates = set()
    rec_ms = D.get('rec_ms', {})
    for fam, obj in rec_ms.items():
        if isinstance(obj, dict):
            sie = obj.get('sie', {})
            for mk in sie:
                candidates.add(mk)
    mol = D.get('mol_perf', {})
    for m, obj in mol.items():
        if not isinstance(obj, dict): continue
        for prod in obj.get('products', []):
            for mk in prod.get('monthly_vals', {}):
                candidates.add(mk)
    if not candidates: return None
    parsed = []
    for mk in candidates:
        parts = mk.split()
        if len(parts) != 2: continue
        m = MES_INV.get(parts[0])
        if not m: continue
        try: y = int(parts[1])
        except: continue
        parsed.append((y, m))
    if not parsed: return None
    parsed.sort()
    return parsed[-1]


def windows_for(end_y, end_m):
    """Define las ventanas current y previa para cada periodo."""
    # Trimestre: ultimos 3 meses vs 3 anteriores
    tri_curr = month_range(end_y, end_m, 3)
    p_y, p_m = add_months(end_y, end_m, -3)
    tri_prev = month_range(p_y, p_m, 3)

    sem_curr = month_range(end_y, end_m, 6)
    p_y, p_m = add_months(end_y, end_m, -6)
    sem_prev = month_range(p_y, p_m, 6)

    mat_curr = month_range(end_y, end_m, 12)
    p_y, p_m = add_months(end_y, end_m, -12)
    mat_prev = month_range(p_y, p_m, 12)

    # YTD: enero del año del cierre hasta el mes del cierre
    ytd_curr = [month_key(end_y, m) for m in range(1, end_m + 1)]
    ytd_prev = [month_key(end_y - 1, m) for m in range(1, end_m + 1)]

    return {
        'ytd':       (ytd_curr, ytd_prev),
        'trimestre': (tri_curr, tri_prev),
        'semestre':  (sem_curr, sem_prev),
        'mat':       (mat_curr, mat_prev),
    }


def sum_window(monthly_dict, window_keys):
    """Suma valores de monthly_dict para los month_keys en window_keys.
    Salta los que no estan presentes (no rellena con 0)."""
    return sum(float(monthly_dict.get(mk, 0) or 0) for mk in window_keys)


def coverage(monthly_dicts, window_keys):
    """Cuantos month_keys de la ventana estan presentes en al menos un dict."""
    covered = 0
    for mk in window_keys:
        if any(mk in d and d[mk] not in (None, 0, '') for d in monthly_dicts):
            covered += 1
    # Tambien chequea presencia (no necesariamente >0): para data presente con valor 0
    presence = 0
    for mk in window_keys:
        if any(mk in d for d in monthly_dicts):
            presence += 1
    return presence


def compute_recetas_kpi(D, window_curr, window_prev):
    """Suma recetas SIE en la ventana sumando rec_ms[fam].sie.
    Devuelve None en prev si la ventana prev no esta cubierta al menos al 80%."""
    rec_ms = D.get('rec_ms', {})
    if not rec_ms:
        return {'sie_curr': 0, 'sie_prev': None, 'mkt_curr': 0, 'mkt_prev': None}
    sie_dicts = [obj.get('sie', {}) for obj in rec_ms.values() if isinstance(obj, dict)]
    cov_curr = coverage(sie_dicts, window_curr)
    cov_prev = coverage(sie_dicts, window_prev)
    sie_curr = sie_prev = 0.0
    mkt_curr = mkt_prev = 0.0
    for fam, obj in rec_ms.items():
        if not isinstance(obj, dict): continue
        sie_m = obj.get('sie', {})
        ms_m  = obj.get('ms', {})
        for mk in window_curr:
            v = float(sie_m.get(mk, 0) or 0)
            sie_curr += v
            ms_pct = float(ms_m.get(mk, 0) or 0)
            mkt_curr += (v / (ms_pct/100.0)) if ms_pct > 0 else v
        for mk in window_prev:
            v = float(sie_m.get(mk, 0) or 0)
            sie_prev += v
            ms_pct = float(ms_m.get(mk, 0) or 0)
            mkt_prev += (v / (ms_pct/100.0)) if ms_pct > 0 else v
    incomplete_prev = cov_prev < len(window_prev) * 0.8
    incomplete_curr = cov_curr < len(window_curr) * 0.8
    return {
        'sie_curr': int(round(sie_curr)) if not incomplete_curr else None,
        'sie_prev': int(round(sie_prev)) if not incomplete_prev else None,
        'mkt_curr': int(round(mkt_curr)) if not incomplete_curr else None,
        'mkt_prev': int(round(mkt_prev)) if not incomplete_prev else None,
    }


def compute_iqvia_kpi(D, window_curr, window_prev):
    """Suma units SIE / market en mol_perf. Marca prev como None si <80% cobertura."""
    mol = D.get('mol_perf', {})
    if not mol:
        return {'sie_curr': 0, 'sie_prev': None, 'mkt_curr': 0, 'mkt_prev': None}
    all_dicts = []
    for obj in mol.values():
        if isinstance(obj, dict):
            for p in obj.get('products', []):
                if p.get('is_sie'):
                    all_dicts.append(p.get('monthly_vals', {}))
    cov_curr = coverage(all_dicts, window_curr)
    cov_prev = coverage(all_dicts, window_prev)
    sie_curr = sie_prev = 0.0
    mkt_curr = mkt_prev = 0.0
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        prods = obj.get('products', [])
        for p in prods:
            mv = p.get('monthly_vals', {})
            is_sie = bool(p.get('is_sie'))
            for mk in window_curr:
                v = float(mv.get(mk, 0) or 0)
                mkt_curr += v
                if is_sie: sie_curr += v
            for mk in window_prev:
                v = float(mv.get(mk, 0) or 0)
                mkt_prev += v
                if is_sie: sie_prev += v
    incomplete_prev = cov_prev < len(window_prev) * 0.8
    incomplete_curr = cov_curr < len(window_curr) * 0.8
    return {
        'sie_curr': int(round(sie_curr)) if not incomplete_curr else None,
        'sie_prev': int(round(sie_prev)) if not incomplete_prev else None,
        'mkt_curr': int(round(mkt_curr)) if not incomplete_curr else None,
        'mkt_prev': int(round(mkt_prev)) if not incomplete_prev else None,
    }


def collect_products(D, window_curr, window_prev, line_key, line_name):
    """Devuelve lista de productos SIE con metricas por la ventana actual."""
    out = []
    mol = D.get('mol_perf', {})
    rec_comp = D.get('rec_comp', {})

    # Para cada producto SIE en mol_perf:
    sie_units_by_prod = {}    # prod_name -> {curr, prev, family}
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        family = obj.get('family', m_key)
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = p.get('prod', '')
            if not name: continue
            mv = p.get('monthly_vals', {})
            curr = sum_window(mv, window_curr)
            prev = sum_window(mv, window_prev)
            # Suma si el producto aparece en multiples moleculas (raro)
            if name in sie_units_by_prod:
                sie_units_by_prod[name]['curr'] += curr
                sie_units_by_prod[name]['prev'] += prev
            else:
                sie_units_by_prod[name] = {
                    'curr': curr, 'prev': prev, 'family': family
                }

    # Recetas SIE por producto: rec_comp[FAM][BRAND] con is_sie=true
    sie_rec_by_prod = {}    # prod_name -> {curr, prev, family}
    for fam, brands in rec_comp.items():
        if not isinstance(brands, dict): continue
        for brand, b in brands.items():
            if not isinstance(b, dict): continue
            if not b.get('is_sie'): continue
            mv = b.get('monthly', {})
            curr = sum_window(mv, window_curr)
            prev = sum_window(mv, window_prev)
            sie_rec_by_prod[brand] = {
                'curr': curr, 'prev': prev, 'family': fam
            }

    # Merge: clave = nombre normalizado
    def norm(s):
        return re.sub(r'\s*\(.*?\)\s*', ' ', str(s)).strip().upper()

    units_by_norm = {norm(k): (k, v) for k, v in sie_units_by_prod.items()}
    rec_by_norm   = {norm(k): (k, v) for k, v in sie_rec_by_prod.items()}

    def safe_ie(c, p):
        if c is None or p is None or p <= 0: return None
        return round(c / p * 100, 1)

    all_keys = set(units_by_norm) | set(rec_by_norm)
    for k in all_keys:
        u_orig, u = units_by_norm.get(k, (None, None))
        r_orig, r = rec_by_norm.get(k, (None, None))
        name = u_orig or r_orig
        family = (r['family'] if r else u['family']) if (r or u) else ''
        rec_curr = int(round(r['curr'])) if r else 0
        rec_prev = int(round(r['prev'])) if r else 0
        u_curr   = int(round(u['curr'])) if u else 0
        u_prev   = int(round(u['prev'])) if u else 0
        out.append({
            'name': name,
            'line': line_key,
            'lineName': line_name,
            'family': family,
            'rec_curr': rec_curr,
            'rec_prev': rec_prev,
            'rec_ie':   safe_ie(rec_curr, rec_prev),
            'units_curr': u_curr,
            'units_prev': u_prev,
            'units_ie':   safe_ie(u_curr, u_prev),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument('--out',  default='kpis.json')
    args = ap.parse_args()

    repo = Path(args.repo)

    # Detectar mes de cierre comun: usar el mas tardio que aparece en mol_perf
    # de cualquier linea (suele ser uniforme = ultimo mes IQVIA cerrado)
    all_data = {}
    latest_per_line = {}
    for line in LINES:
        kind, rel = line['source']
        path = repo / rel
        if not path.is_file():
            print(f'  [{line["key"]}] SKIP: no existe {path}')
            continue
        D = load_inline(path) if kind == 'inline' else load_data_js(path)
        if not D:
            print(f'  [{line["key"]}] SKIP: no parseable')
            continue
        all_data[line['key']] = D
        latest = find_latest_month_in_data(D)
        if latest:
            latest_per_line[line['key']] = latest
            print(f'  [{line["key"]}] cierre detectado: {month_key(*latest)}')

    if not latest_per_line:
        print('ERROR: ninguna linea con data', file=sys.stderr)
        return 2

    # Cierre global = el mas grande (mas reciente)
    end_y, end_m = max(latest_per_line.values())
    print(f'\nCierre global: {month_key(end_y, end_m)}')
    windows = windows_for(end_y, end_m)

    out = {
        'generated_at': __import__('datetime').datetime.now().isoformat(timespec='seconds'),
        'as_of_month': month_key(end_y, end_m),
        'periods': list(windows.keys()),
        'period_labels': {
            'ytd': f'YTD {end_y} (Ene–{MES_EN[end_m]})',
            'trimestre': f'Últ. 3 meses ({windows["trimestre"][0][0]} – {windows["trimestre"][0][-1]})',
            'semestre':  f'Últ. 6 meses ({windows["semestre"][0][0]} – {windows["semestre"][0][-1]})',
            'mat':       f'MAT 12 meses ({windows["mat"][0][0]} – {windows["mat"][0][-1]})',
        },
        'lines': [],
        'products': [],
    }

    for line in LINES:
        D = all_data.get(line['key'])
        if not D:
            print(f'  [{line["key"]}] sin data, skip en output')
            continue

        kpis = {}
        for period, (curr, prev) in windows.items():
            rec = compute_recetas_kpi(D, curr, prev)
            iqvia = compute_iqvia_kpi(D, curr, prev)
            def safe_ms(num, den):
                if num is None or den is None or den == 0: return None
                return round(num/den*100, 2)
            def safe_ie(c, p):
                """IE = (curr/prev)*100. None si prev<=0 o falta."""
                if c is None or p is None or p <= 0: return None
                return round(c / p * 100, 1)
            kpis[period] = {
                'recetas_sie':   {'curr': rec['sie_curr'],   'prev': rec['sie_prev'],
                                  'ie': safe_ie(rec['sie_curr'], rec['sie_prev'])},
                'ms_recetas':    {'curr': safe_ms(rec['sie_curr'], rec['mkt_curr']),
                                  'prev': safe_ms(rec['sie_prev'], rec['mkt_prev'])},
                'mercado_recetas': {'curr': rec['mkt_curr'], 'prev': rec['mkt_prev'],
                                    'ie': safe_ie(rec['mkt_curr'], rec['mkt_prev'])},
                'units_sie':     {'curr': iqvia['sie_curr'], 'prev': iqvia['sie_prev'],
                                  'ie': safe_ie(iqvia['sie_curr'], iqvia['sie_prev'])},
                'ms_units':      {'curr': safe_ms(iqvia['sie_curr'], iqvia['mkt_curr']),
                                  'prev': safe_ms(iqvia['sie_prev'], iqvia['mkt_prev'])},
                'mercado_units': {'curr': iqvia['mkt_curr'], 'prev': iqvia['mkt_prev'],
                                  'ie': safe_ie(iqvia['mkt_curr'], iqvia['mkt_prev'])},
            }
        out['lines'].append({
            'key':   line['key'],
            'name':  line['name'],
            'icon':  line['icon'],
            'color': line['color'],
            'href':  line['href'],
            'owner': line['owner'],
            'kpis':  kpis,
        })

        # Productos: solo los que tienen units OR recetas en YTD curr
        ytd_curr, ytd_prev = windows['ytd']
        prods = collect_products(D, ytd_curr, ytd_prev, line['key'], line['name'])
        prods = [p for p in prods if p['rec_curr'] > 0 or p['units_curr'] > 0]
        # Tambien metemos el resumen YTD para tabla por producto
        out['products'].extend(prods)

    out['products'].sort(key=lambda p: p['rec_curr'] + p['units_curr'], reverse=True)

    out_path = repo / args.out
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                        encoding='utf-8', newline='')
    print(f'\n-> {out_path} ({out_path.stat().st_size:,} bytes)')
    print(f'   Lineas con KPIs: {len(out["lines"])}')
    print(f'   Productos SIE en tabla: {len(out["products"])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
