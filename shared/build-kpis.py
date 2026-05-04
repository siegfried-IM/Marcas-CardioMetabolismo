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
    {'key':'otx',     'name':'OTC',              'icon':'🩹', 'color':'#0284C7',
     'href':'OTC/',           'owner':'Tatiana Peker',
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


def find_latest_in_keys(month_keys):
    """Devuelve (year, month_num) del month_key mas reciente, o None."""
    parsed = []
    for mk in month_keys:
        parts = str(mk).split()
        if len(parts) != 2: continue
        m = MES_INV.get(parts[0])
        if not m: continue
        try: y = int(parts[1])
        except: continue
        parsed.append((y, m))
    if not parsed: return None
    parsed.sort()
    return parsed[-1]


def find_latest_recetas(D):
    """Ultimo mes con data en rec_ms.sie."""
    keys = set()
    for fam, obj in D.get('rec_ms', {}).items():
        if isinstance(obj, dict):
            keys.update(obj.get('sie', {}).keys())
    return find_latest_in_keys(keys)


def find_latest_iqvia(D):
    """Ultimo mes con data en mol_perf (cualquier producto)."""
    keys = set()
    for mol in D.get('mol_perf', {}).values():
        if not isinstance(mol, dict): continue
        for p in mol.get('products', []):
            keys.update(p.get('monthly_vals', {}).keys())
    return find_latest_in_keys(keys)


def find_latest_month_in_data(D):
    """Para reportar el cierre general de la linea (max entre recetas/iqvia)."""
    cands = []
    a = find_latest_recetas(D)
    b = find_latest_iqvia(D)
    if a: cands.append(a)
    if b: cands.append(b)
    if not cands: return None
    cands.sort()
    return cands[-1]


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


def collect_products(D, window_curr, window_prev, line_key, line_name,
                     rec_window_curr=None, rec_window_prev=None):
    """Devuelve lista de productos SIE con metricas por la ventana actual.

    Estrategia para recetas por producto SIE:
      1) rec_comp[fam][brand].is_sie=true con monthly  -> brand-level (mujer
         post-D3 patch).
      2) Si el SIE producto es el unico SIE en su family/mol_perf key, usar
         rec_ms[fam].sie como aproximacion family-level.
      3) Si hay multiples SIE en la familia, repartir proporcionalmente por
         units en la ventana, OR atribuir total al primero.

    rec_window_* son ventanas paralelas para recetas (puede tener cutoff
    distinto que units). Si None, usa window_curr/prev."""
    if rec_window_curr is None: rec_window_curr = window_curr
    if rec_window_prev is None: rec_window_prev = window_prev

    out = []
    mol = D.get('mol_perf', {})
    rec_comp = D.get('rec_comp', {})
    rec_ms = D.get('rec_ms', {})

    # 1) Recoger SIE products de mol_perf con units
    sie_units_by_prod = {}    # prod_name -> {curr, prev, family, fam_key}
    sie_per_fam = defaultdict(list)  # fam_key -> [prod_name, ...] de productos SIE
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
            if name in sie_units_by_prod:
                sie_units_by_prod[name]['curr'] += curr
                sie_units_by_prod[name]['prev'] += prev
            else:
                sie_units_by_prod[name] = {
                    'curr': curr, 'prev': prev,
                    'family': family, 'fam_key': m_key
                }
                sie_per_fam[m_key].append(name)

    # 2) Recetas explicitas por brand (rec_comp[fam][brand].is_sie=true)
    sie_rec_explicit = {}    # prod_name -> {curr, prev, family}
    for fam, brands in rec_comp.items():
        if not isinstance(brands, dict): continue
        for brand, b in brands.items():
            if not isinstance(b, dict): continue
            if not b.get('is_sie'): continue
            mv = b.get('monthly', {})
            curr = sum_window(mv, rec_window_curr)
            prev = sum_window(mv, rec_window_prev)
            sie_rec_explicit[brand] = {
                'curr': curr, 'prev': prev, 'family': fam
            }

    # Helper: normalizar nombre para matching mol_perf <-> rec_comp
    def norm(s):
        return re.sub(r'\s*\(.*?\)\s*', ' ', str(s)).strip().upper()

    sie_rec_by_norm = {norm(k): (k, v) for k, v in sie_rec_explicit.items()}

    # 3) Para SIE products que NO tienen explicit rec_comp, usar rec_ms[fam].sie
    #    Si la familia tiene multiples SIE products, repartimos por
    #    units share dentro de la familia.
    #
    #    Para matchear fam_key (mol_perf key) contra rec_ms key, probamos:
    #      a) Exact: fam_key in rec_ms
    #      b) Family field: mol[fam_key].family in rec_ms
    #      c) Per-product: para cada SIE prod en la familia, probar
    #         normalizaciones del nombre (e.g. 'VALIUM (SIE)' -> 'VALIUM SIE')
    sie_rec_per_prod = {}  # prod_name -> {curr, prev} via family-level lookup

    def strip_paren(name):
        return re.sub(r'\s*\(.*?\)\s*$', '', str(name)).strip()

    fam_sie_recetas = {}  # fam_key -> {curr, prev}
    for fam_key in sie_per_fam:
        fam_field = mol.get(fam_key, {}).get('family', '') if isinstance(mol.get(fam_key), dict) else ''
        candidates = [fam_key, fam_field]
        rec_ms_obj = None
        for c in candidates:
            if c in rec_ms and isinstance(rec_ms[c], dict):
                rec_ms_obj = rec_ms[c]
                break
        if rec_ms_obj is not None:
            sie_m = rec_ms_obj.get('sie', {})
            if isinstance(sie_m, dict) and sie_m:
                curr = sum_window(sie_m, rec_window_curr)
                prev = sum_window(sie_m, rec_window_prev)
                fam_sie_recetas[fam_key] = {'curr': curr, 'prev': prev}
                continue

        # Fallback: try per-SIE-product matching (caso SNC: rec_ms keyed por
        # 'VALIUM SIE', 'MADOPAR SIE', 'PGB MULTIDOSIS SIE', mol_perf keyed por molecule)
        for prod_name in sie_per_fam[fam_key]:
            base = strip_paren(prod_name)
            base_upper = base.upper()
            # Exact attempts first
            attempts = [f'{base} SIE', base, f'{base_upper} SIE']
            matched = False
            for cand in attempts:
                if cand in rec_ms and isinstance(rec_ms[cand], dict):
                    sie_m = rec_ms[cand].get('sie', {})
                    if isinstance(sie_m, dict) and sie_m:
                        curr = sum_window(sie_m, rec_window_curr)
                        prev = sum_window(sie_m, rec_window_prev)
                        sie_rec_per_prod[prod_name] = {'curr': curr, 'prev': prev}
                        matched = True
                        break
            if matched: continue
            # Loose: rec_ms key starts with base + ' ' (e.g., 'PGB MULTIDOSIS SIE')
            for k in rec_ms:
                if isinstance(rec_ms[k], dict) and k.upper().startswith(base_upper + ' '):
                    sie_m = rec_ms[k].get('sie', {})
                    if isinstance(sie_m, dict) and sie_m:
                        curr = sum_window(sie_m, rec_window_curr)
                        prev = sum_window(sie_m, rec_window_prev)
                        sie_rec_per_prod[prod_name] = {'curr': curr, 'prev': prev}
                        break

    def safe_ie(c, p):
        if c is None or p is None or p <= 0: return None
        return round(c / p * 100, 1)

    # Construir lista final: union de SIE products en units + explicit rec
    seen = set()
    for prod_name, u_info in sie_units_by_prod.items():
        n = norm(prod_name)
        seen.add(n)
        # Recetas: prefer explicit rec_comp, sino per-prod, sino fam_sie repartido
        rec_explicit = sie_rec_by_norm.get(n)
        per_prod = sie_rec_per_prod.get(prod_name)
        if rec_explicit:
            r_curr = rec_explicit[1]['curr']
            r_prev = rec_explicit[1]['prev']
            family = rec_explicit[1]['family']
        elif per_prod:
            r_curr = per_prod['curr']
            r_prev = per_prod['prev']
            family = u_info['family']
        else:
            family = u_info['family']
            fam_key = u_info['fam_key']
            fam_rec = fam_sie_recetas.get(fam_key)
            if not fam_rec:
                r_curr = r_prev = 0
            else:
                # Si solo hay un SIE en la familia, atribuir total
                sie_in_fam = sie_per_fam[fam_key]
                if len(sie_in_fam) <= 1:
                    r_curr = fam_rec['curr']
                    r_prev = fam_rec['prev']
                else:
                    # Repartir por units share en la ventana curr
                    total_units = sum(sie_units_by_prod[n2]['curr'] for n2 in sie_in_fam)
                    if total_units > 0:
                        share = u_info['curr'] / total_units
                        r_curr = fam_rec['curr'] * share
                        r_prev = fam_rec['prev'] * share
                    else:
                        # Sin units, dividir parejo
                        r_curr = fam_rec['curr'] / len(sie_in_fam)
                        r_prev = fam_rec['prev'] / len(sie_in_fam)

        rec_curr = int(round(r_curr))
        rec_prev = int(round(r_prev))
        u_curr = int(round(u_info['curr']))
        u_prev = int(round(u_info['prev']))
        out.append({
            'name': prod_name,
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

    # Tambien incluir SIE products que tienen explicit rec_comp pero no estan
    # en mol_perf (poco frecuente)
    for n, (orig_name, info) in sie_rec_by_norm.items():
        if n in seen: continue
        rec_curr = int(round(info['curr']))
        rec_prev = int(round(info['prev']))
        out.append({
            'name': orig_name,
            'line': line_key,
            'lineName': line_name,
            'family': info['family'],
            'rec_curr': rec_curr,
            'rec_prev': rec_prev,
            'rec_ie':   safe_ie(rec_curr, rec_prev),
            'units_curr': 0,
            'units_prev': 0,
            'units_ie':   None,
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

        # Per-line cutoffs por metrica (para que ninguna linea quede sin
        # comparable solo porque mol_perf llega 1 mes mas tarde que recetas)
        rec_latest = find_latest_recetas(D)
        iq_latest  = find_latest_iqvia(D)
        rec_windows = windows_for(*rec_latest) if rec_latest else None
        iq_windows  = windows_for(*iq_latest)  if iq_latest  else None
        rec_cut = month_key(*rec_latest) if rec_latest else None
        iq_cut  = month_key(*iq_latest)  if iq_latest  else None
        print(f'  [{line["key"]}] cutoffs: recetas={rec_cut or "—"}, iqvia={iq_cut or "—"}')

        kpis = {}
        for period in ['ytd', 'trimestre', 'semestre', 'mat']:
            r_curr, r_prev = rec_windows[period] if rec_windows else ([], [])
            i_curr, i_prev = iq_windows[period]  if iq_windows  else ([], [])
            rec = compute_recetas_kpi(D, r_curr, r_prev)
            iqvia = compute_iqvia_kpi(D, i_curr, i_prev)
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
            'recetas_through': rec_cut,
            'iqvia_through':   iq_cut,
            'kpis':  kpis,
        })

        # Productos: union de cutoffs de la linea para YTD
        # (units usa iq_cut, recetas usa rec_cut)
        if iq_windows:
            iq_ytd_curr, iq_ytd_prev = iq_windows['ytd']
        else:
            iq_ytd_curr = iq_ytd_prev = []
        if rec_windows:
            rec_ytd_curr, rec_ytd_prev = rec_windows['ytd']
        else:
            rec_ytd_curr = rec_ytd_prev = []
        # Para units usamos iq_windows; para recetas, rec_windows (puede tener cutoff distinto)
        ytd_curr, ytd_prev = (iq_ytd_curr, iq_ytd_prev) if iq_ytd_curr else (rec_ytd_curr, rec_ytd_prev)
        prods = collect_products(D, ytd_curr, ytd_prev, line['key'], line['name'],
                                  rec_window_curr=rec_ytd_curr, rec_window_prev=rec_ytd_prev)
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
