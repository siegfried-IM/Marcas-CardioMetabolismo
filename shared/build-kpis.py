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

# Lineas que NO tienen recetas trackeadas (CloseUp). Para estas, las metricas
# de recetas se setean a null en el output para no mostrar data engañosa.
LINES_NO_RECETAS = set()

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
    """Define las ventanas current y previa para cada periodo.

    TODOS los periodos comparan vs el MISMO periodo del año anterior:
      - mensual:   ultimo mes      vs mismo mes año -1
      - trimestre: ultimos 3 meses vs mismos 3 meses año -1
      - semestre:  ultimos 6 meses vs mismos 6 meses año -1
      - ytd:       Ene..cierre     vs mismo rango año -1
      - mat:       ultimos 12 mes  vs prev 12 (= same period año -1)
    """
    # Mensual: solo el ultimo mes
    men_curr = [month_key(end_y, end_m)]
    men_prev = [month_key(end_y - 1, end_m)]

    # Trimestre: ultimos 3 meses (rolling) vs mismos 3 meses año anterior
    tri_curr = month_range(end_y, end_m, 3)
    p_y, p_m = add_months(end_y, end_m, -12)
    tri_prev = month_range(p_y, p_m, 3)

    # Semestre: ultimos 6 vs mismos 6 año anterior
    sem_curr = month_range(end_y, end_m, 6)
    p_y, p_m = add_months(end_y, end_m, -12)
    sem_prev = month_range(p_y, p_m, 6)

    # MAT: ultimos 12 vs prev 12 (= mismos meses año anterior por definicion)
    mat_curr = month_range(end_y, end_m, 12)
    p_y, p_m = add_months(end_y, end_m, -12)
    mat_prev = month_range(p_y, p_m, 12)

    # YTD: Ene..cierre vs mismo rango año anterior
    ytd_curr = [month_key(end_y, m) for m in range(1, end_m + 1)]
    ytd_prev = [month_key(end_y - 1, m) for m in range(1, end_m + 1)]

    return {
        'mensual':   (men_curr, men_prev),
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
    # Sumar PER-FAMILY con inclusion simetrica: si el month_key falta en
    # curr para una familia, tambien se excluye del prev (y viceversa).
    # Esto evita falsos drops cuando una familia tiene Mar 2025 pero no
    # Mar 2026 (data parcial / no actualizada).
    for fam, obj in rec_ms.items():
        if not isinstance(obj, dict): continue
        sie_m = obj.get('sie', {})
        ms_m  = obj.get('ms', {})
        # Por posicion: window_curr y window_prev deben tener mismo length
        # y representar mismos meses-de-año (Ene curr <-> Ene prev, etc).
        for i, (mk_c, mk_p) in enumerate(zip(window_curr, window_prev)):
            has_c = mk_c in sie_m
            has_p = mk_p in sie_m
            if not (has_c and has_p):
                continue   # skip ambos si falta uno
            v_c = float(sie_m.get(mk_c, 0) or 0)
            v_p = float(sie_m.get(mk_p, 0) or 0)
            sie_curr += v_c
            sie_prev += v_p
            ms_c = float(ms_m.get(mk_c, 0) or 0)
            ms_p = float(ms_m.get(mk_p, 0) or 0)
            mkt_curr += (v_c / (ms_c/100.0)) if ms_c > 0 else v_c
            mkt_prev += (v_p / (ms_p/100.0)) if ms_p > 0 else v_p
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

    # Primer pase: identificar la family "primary" de cada SIE product.
    # Primary = la family cuyo m_key = base_name del producto. Si no hay,
    # se usa la primera ocurrencia.
    sie_primary_fam = {}  # name -> m_key primary
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = p.get('prod', '')
            if not name: continue
            base_name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip().upper()
            is_primary = (base_name == m_key.upper())
            if name not in sie_primary_fam or is_primary:
                sie_primary_fam[name] = m_key

    # Segundo pase: agregar mkt (todos los products incl competidores) y
    # SIE solo en la primary family.
    sie_curr = sie_prev = 0.0
    mkt_curr = mkt_prev = 0.0
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        for p in obj.get('products', []):
            mv = p.get('monthly_vals', {})
            is_sie = bool(p.get('is_sie'))
            name = p.get('prod', '')
            for mk in window_curr:
                v = float(mv.get(mk, 0) or 0)
                mkt_curr += v
                if is_sie and sie_primary_fam.get(name) == m_key:
                    sie_curr += v
            for mk in window_prev:
                v = float(mv.get(mk, 0) or 0)
                mkt_prev += v
                if is_sie and sie_primary_fam.get(name) == m_key:
                    sie_prev += v
    incomplete_prev = cov_prev < len(window_prev) * 0.8
    incomplete_curr = cov_curr < len(window_curr) * 0.8
    return {
        'sie_curr': int(round(sie_curr)) if not incomplete_curr else None,
        'sie_prev': int(round(sie_prev)) if not incomplete_prev else None,
        'mkt_curr': int(round(mkt_curr)) if not incomplete_curr else None,
        'mkt_prev': int(round(mkt_prev)) if not incomplete_prev else None,
    }


def _sum_budget_real(target, window_curr, window_prev):
    """Helper: dado un budget[KEY] dict ({YYYY: {real:[m1..m12]}}),
    devuelve (suma_curr, suma_prev) sumando los meses de window_curr/prev."""
    monthly_real = {}
    for year_str, year_data in target.items():
        if not isinstance(year_data, dict): continue
        real_arr = year_data.get('real', [])
        if not isinstance(real_arr, list): continue
        try: year = int(year_str)
        except ValueError: continue
        for i, v in enumerate(real_arr):
            if v is None or v == 0 or i >= 12: continue
            mk = f'{MES_EN[i+1]} {year}'
            monthly_real[mk] = float(v)
    curr = sum(monthly_real.get(mk, 0) for mk in window_curr)
    prev = sum(monthly_real.get(mk, 0) for mk in window_prev)
    return (curr, prev)


def get_internal_sales(D, prod_name, fam_key, window_curr, window_prev,
                       is_primary=True):
    """Devuelve (curr, prev) de venta interna del SIE product.

    Busca budget[KEY].YYYY.real con KEY en este orden:
      1) prod_name exacto
      2) prod_name sin '(SIE)' o ' SIE'
      3) fam_key del mol_perf — pero solo si is_primary=True (sino
         seria double-count para variantes que comparten budget de
         familia)
    Si encuentra, suma los meses del window."""
    budget = D.get('budget', {})
    if not budget: return (None, None)

    base = re.sub(r'\s*\(.*?\)\s*$', '', str(prod_name)).strip()
    base = re.sub(r'\s+SIE\s*$', '', base, flags=re.I).strip()
    # Probar match directo primero
    target = None
    for c in [prod_name, base]:
        if c and c in budget and isinstance(budget[c], dict):
            target = budget[c]; break
    # Fallback al fam_key SOLO si este es el primary del family
    if target is None and is_primary and fam_key and fam_key in budget:
        if isinstance(budget[fam_key], dict):
            target = budget[fam_key]
    if target is None: return (None, None)

    monthly_real = {}
    for year_str, year_data in target.items():
        if not isinstance(year_data, dict): continue
        real_arr = year_data.get('real', [])
        if not isinstance(real_arr, list): continue
        try:
            year = int(year_str)
        except ValueError:
            continue
        for i, v in enumerate(real_arr):
            if v is None or v == 0: continue
            if i >= 12: continue
            mk = f'{MES_EN[i+1]} {year}'
            monthly_real[mk] = float(v)

    curr = sum(monthly_real.get(mk, 0) for mk in window_curr)
    prev = sum(monthly_real.get(mk, 0) for mk in window_prev)
    return (curr, prev)


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

    # 1) Recoger SIE products de mol_perf con units.
    # Algunas familias de mol_perf incluyen el producto padre (ej. mol_perf
    # [DILATREND AP].products contiene DILATREND (SIE) ademas de DILATREND
    # AP (SIE)). Para evitar double-count, usamos la PRIMERA ocurrencia del
    # producto en su family "primary" (la que mas matchea el nombre).
    sie_units_by_prod = {}    # prod_name -> {curr, prev, family, fam_key}
    sie_per_fam = defaultdict(list)  # fam_key -> [prod_name, ...] de productos SIE primary
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        family = obj.get('family', m_key)
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = p.get('prod', '')
            if not name: continue
            # Determinar si esta es la "primary" family de este producto.
            # Heuristica: la family donde el nombre del producto sin (SIE)
            # matchea el m_key (e.g. DILATREND (SIE) -> DILATREND).
            base_name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip().upper()
            is_primary = (base_name == m_key.upper())
            mv = p.get('monthly_vals', {})
            curr = sum_window(mv, window_curr)
            prev = sum_window(mv, window_prev)
            existing = sie_units_by_prod.get(name)
            if existing:
                # Si el existente NO era primary y este SI lo es, reemplazar.
                # Sino, ignorar duplicado (no sumar).
                if is_primary and not existing.get('is_primary'):
                    sie_per_fam[existing['fam_key']].remove(name)
                    sie_units_by_prod[name] = {
                        'curr': curr, 'prev': prev,
                        'family': family, 'fam_key': m_key,
                        'is_primary': True,
                    }
                    sie_per_fam[m_key].append(name)
                # else: skip (duplicado)
            else:
                sie_units_by_prod[name] = {
                    'curr': curr, 'prev': prev,
                    'family': family, 'fam_key': m_key,
                    'is_primary': is_primary,
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
    # 'HEXALER NASAL (SIE)'         -> 'HEXALERNASAL'
    # 'HEXALER NASAL SIE'           -> 'HEXALERNASAL'
    # 'ACEMUK DIAYNOCHE SIE'        -> 'ACEMUKDIAYNOCHE'
    # 'ACEMUK DIA Y NOCHE (SIE)'    -> 'ACEMUKDIAYNOCHE' (whitespace colapsado)
    def norm(s):
        s = str(s).strip().upper()
        s = re.sub(r'\s*\([^)]*\)\s*$', '', s)        # quitar (SIE) final
        s = re.sub(r'\s+SIE\s*$', '', s)               # quitar ' SIE' final
        s = re.sub(r'[^A-Z0-9]+', '', s)               # eliminar puntuación + espacios
        return s.strip()

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

    def find_recms_match(key):
        """Devuelve rec_ms[k] tras probar exact match o case-insensitive.
        NO hace prefix-strip (causaba mal-atribucion: ACEMUK L SIE no
        deberia heredar rec de ACEMUK)."""
        if not key: return None
        if key in rec_ms and isinstance(rec_ms[key], dict):
            return rec_ms[key]
        rms_lower = {k.upper(): k for k in rec_ms}
        cu = key.upper()
        if cu in rms_lower:
            k = rms_lower[cu]
            if isinstance(rec_ms[k], dict): return rec_ms[k]
        return None

    fam_sie_recetas = {}  # fam_key -> {curr, prev}
    for fam_key in sie_per_fam:
        fam_field = mol.get(fam_key, {}).get('family', '') if isinstance(mol.get(fam_key), dict) else ''
        rec_ms_obj = find_recms_match(fam_key) or find_recms_match(fam_field)
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
    # Solo incluimos productos que tienen alguna fuente de recetas trackeada
    # (sino quedan con rec=0 confuso). Si NO esta trackeado en rec_ms/rec_comp/
    # recetas de la linea, se filtra.
    seen = set()
    for prod_name, u_info in sie_units_by_prod.items():
        n = norm(prod_name)
        seen.add(n)
        # Recetas: prefer explicit rec_comp, sino per-prod, sino fam_sie repartido
        rec_explicit = sie_rec_by_norm.get(n)
        per_prod = sie_rec_per_prod.get(prod_name)
        has_rec_source = False
        if rec_explicit:
            r_curr = rec_explicit[1]['curr']
            r_prev = rec_explicit[1]['prev']
            family = rec_explicit[1]['family']
            has_rec_source = True
        elif per_prod:
            r_curr = per_prod['curr']
            r_prev = per_prod['prev']
            family = u_info['family']
            has_rec_source = True
        else:
            family = u_info['family']
            fam_key = u_info['fam_key']
            fam_rec = fam_sie_recetas.get(fam_key)
            if not fam_rec:
                r_curr = r_prev = 0
                has_rec_source = False
            else:
                has_rec_source = True
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

        # Si el producto NO tiene fuente de recetas trackeada, lo skip
        # para que la tabla quede consistente (todos los SIE en la tabla
        # tienen al menos algun dato de recetas en la linea).
        if not has_rec_source:
            continue

        rec_curr = int(round(r_curr))
        rec_prev = int(round(r_prev))
        u_curr = int(round(u_info['curr']))
        u_prev = int(round(u_info['prev']))

        # Venta interna (budget.real) por SIE product.
        # Estrategia: budget[FAM_KEY] cubre TODOS los SIE products del
        # family. Lo repartimos proporcionalmente por units share IQVIA
        # (igual que ya hacemos con recetas). Si un producto tiene su
        # propio budget exacto (ej. BACTRIM FORTE -> budget[BACTRIM FORTE]),
        # se usa directamente y no se reparte.
        int_curr_v = int_prev_v = None
        budget = D.get('budget', {})
        base = re.sub(r'\s*\(.*?\)\s*$', '', str(prod_name)).strip()
        base = re.sub(r'\s+SIE\s*$', '', base, flags=re.I).strip()
        # Si el producto tiene fam_key DIFERENTE del fam parent (ej.
        # BACTRIM FORTE -> fam_key='BACTRIM FORTE'), match exacto.
        # Si fam_key matchea base_name (es primary), tambien match.
        own_budget_key = None
        for c in [prod_name, base]:
            if c and c in budget and isinstance(budget[c], dict):
                own_budget_key = c; break
        # Si own_budget_key != fam_key, hay match propio especifico:
        # usar tal cual sin reparto (porque budget no cubre siblings).
        if own_budget_key and own_budget_key != u_info['fam_key']:
            int_curr_v, int_prev_v = _sum_budget_real(
                budget[own_budget_key], rec_window_curr, rec_window_prev)
        elif u_info['fam_key'] and u_info['fam_key'] in budget:
            # Family budget — repartir entre TODOS los SIE products de
            # esta family por units share. (Si solo hay 1 SIE en family,
            # share=1.0 y se atribuye total.)
            fam_budget = budget[u_info['fam_key']]
            siblings = sie_per_fam.get(u_info['fam_key'], [])
            total_u = sum(sie_units_by_prod[n].get('curr', 0) for n in siblings)
            if total_u > 0:
                share = u_info['curr'] / total_u
            else:
                share = 1.0 / max(len(siblings), 1)
            fam_c, fam_p = _sum_budget_real(fam_budget, rec_window_curr, rec_window_prev)
            int_curr_v = (fam_c * share) if fam_c is not None else None
            int_prev_v = (fam_p * share) if fam_p is not None else None
        int_curr_int = int(round(int_curr_v)) if int_curr_v is not None else None
        int_prev_int = int(round(int_prev_v)) if int_prev_v is not None else None

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
            'int_curr':  int_curr_int,
            'int_prev':  int_prev_int,
            'int_ie':    safe_ie(int_curr_int, int_prev_int),
        })

    # Tambien incluir SIE products que tienen explicit rec_comp pero no estan
    # en mol_perf (poco frecuente)
    for n, (orig_name, info) in sie_rec_by_norm.items():
        if n in seen: continue
        rec_curr = int(round(info['curr']))
        rec_prev = int(round(info['prev']))
        int_curr, int_prev = get_internal_sales(D, orig_name, info['family'],
                                                  rec_window_curr, rec_window_prev)
        int_curr_int = int(round(int_curr)) if int_curr is not None else None
        int_prev_int = int(round(int_prev)) if int_prev is not None else None
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
            'int_curr':  int_curr_int,
            'int_prev':  int_prev_int,
            'int_ie':    safe_ie(int_curr_int, int_prev_int),
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
            'mensual':   f'{windows["mensual"][0][0]} vs {windows["mensual"][1][0]}',
            'ytd':       f'YTD {end_y} (Ene–{MES_EN[end_m]}) vs {end_y-1}',
            'trimestre': f'Últ. trimestre ({windows["trimestre"][0][0]} – {windows["trimestre"][0][-1]}) vs año -1',
            'semestre':  f'Últ. semestre ({windows["semestre"][0][0]} – {windows["semestre"][0][-1]}) vs año -1',
            'mat':       f'MAT 12 meses ({windows["mat"][0][0]} – {windows["mat"][0][-1]}) vs año -1',
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

        line_no_rec = line['key'] in LINES_NO_RECETAS

        # Compute per-line internal sales (suma de budget[fam].YYYY.real)
        def line_internal_sales(window_keys):
            total = 0.0
            for fam_key, fam_b in D.get('budget', {}).items():
                if not isinstance(fam_b, dict): continue
                for year_str, year_data in fam_b.items():
                    if not isinstance(year_data, dict): continue
                    real_arr = year_data.get('real', [])
                    if not isinstance(real_arr, list): continue
                    try: year = int(year_str)
                    except ValueError: continue
                    for i, v in enumerate(real_arr):
                        if v is None or i >= 12: continue
                        mk = f'{MES_EN[i+1]} {year}'
                        if mk in window_keys:
                            total += float(v)
            return int(round(total))

        kpis = {}
        for period in ['mensual', 'ytd', 'trimestre', 'semestre', 'mat']:
            r_curr, r_prev = rec_windows[period] if rec_windows else ([], [])
            i_curr, i_prev = iq_windows[period]  if iq_windows  else ([], [])
            if line_no_rec:
                rec = {'sie_curr': None, 'sie_prev': None, 'mkt_curr': None, 'mkt_prev': None}
            else:
                rec = compute_recetas_kpi(D, r_curr, r_prev)
            iqvia = compute_iqvia_kpi(D, i_curr, i_prev)
            # Internal sales (sum of all family budget.real). Periodos compartidos
            # con iqvia (mismo cierre por linea).
            int_curr = line_internal_sales(set(i_curr)) if i_curr else None
            int_prev = line_internal_sales(set(i_prev)) if i_prev else None
            if int_curr == 0 and int_prev == 0:
                int_curr = int_prev = None
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
                'venta_interna': {'curr': int_curr, 'prev': int_prev,
                                  'ie': safe_ie(int_curr, int_prev)},
            }
        out['lines'].append({
            'key':   line['key'],
            'name':  line['name'],
            'icon':  line['icon'],
            'color': line['color'],
            'href':  line['href'],
            'owner': line['owner'],
            'recetas_through': None if line_no_rec else rec_cut,
            'iqvia_through':   iq_cut,
            'has_recetas':     not line_no_rec,
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
        # Por producto: computar TODOS los periodos para que la UI pueda
        # cambiar el filtro y ver los numeros correctos sin re-fetch.
        period_kpis_per_prod = {}  # prod_name -> {period: kpi_dict}
        prods_seen = []  # ordered list of products (key=name)
        prod_meta = {}   # prod_name -> {family, fam_key}

        for period in ['mensual', 'ytd', 'trimestre', 'semestre', 'mat']:
            r_curr, r_prev = rec_windows[period] if rec_windows else ([], [])
            i_curr, i_prev = iq_windows[period]  if iq_windows  else ([], [])

            if line_no_rec:
                # Linea sin recetas: solo units + venta interna
                for m_key, fam_obj in D.get('mol_perf', {}).items():
                    if not isinstance(fam_obj, dict): continue
                    family = fam_obj.get('family', m_key)
                    for p in fam_obj.get('products', []):
                        if not p.get('is_sie'): continue
                        name = p.get('prod', '')
                        if not name: continue
                        mv = p.get('monthly_vals', {})
                        u_curr = int(round(sum_window(mv, i_curr)))
                        u_prev = int(round(sum_window(mv, i_prev)))
                        int_c, int_p = get_internal_sales(D, name, m_key, i_curr, i_prev)
                        int_c = int(round(int_c)) if int_c is not None else None
                        int_p = int(round(int_p)) if int_p is not None else None
                        if name not in period_kpis_per_prod:
                            period_kpis_per_prod[name] = {}
                            prods_seen.append(name)
                            prod_meta[name] = {'family': family, 'fam_key': m_key}
                        period_kpis_per_prod[name][period] = {
                            'rec_curr': None, 'rec_prev': None, 'rec_ie': None,
                            'units_curr': u_curr, 'units_prev': u_prev,
                            'units_ie': (round(u_curr/u_prev*100,1) if u_prev>0 else None),
                            'int_curr': int_c, 'int_prev': int_p,
                            'int_ie': (round(int_c/int_p*100,1) if int_p and int_p>0 else None),
                        }
            else:
                period_prods = collect_products(D, i_curr, i_prev, line['key'], line['name'],
                                                  rec_window_curr=r_curr, rec_window_prev=r_prev)
                for p in period_prods:
                    name = p['name']
                    if name not in period_kpis_per_prod:
                        period_kpis_per_prod[name] = {}
                        prods_seen.append(name)
                        prod_meta[name] = {'family': p['family'], 'fam_key': None}
                    period_kpis_per_prod[name][period] = {
                        'rec_curr': p['rec_curr'], 'rec_prev': p['rec_prev'], 'rec_ie': p['rec_ie'],
                        'units_curr': p['units_curr'], 'units_prev': p['units_prev'], 'units_ie': p['units_ie'],
                        'int_curr': p['int_curr'], 'int_prev': p['int_prev'], 'int_ie': p['int_ie'],
                    }

        # Filtrar productos: deben tener al menos algun dato en YTD
        prods = []
        for name in prods_seen:
            ytd = period_kpis_per_prod[name].get('ytd', {})
            has_data = ((ytd.get('rec_curr') or 0) > 0
                        or (ytd.get('units_curr') or 0) > 0
                        or (ytd.get('int_curr') or 0) > 0)
            if not has_data: continue
            meta = prod_meta[name]
            prods.append({
                'name': name,
                'line': line['key'],
                'lineName': line['name'],
                'family': meta['family'],
                'periods': period_kpis_per_prod[name],
            })
        # Tambien metemos el resumen YTD para tabla por producto
        out['products'].extend(prods)

    def prod_sort_key(p):
        ytd = p.get('periods', {}).get('ytd', {})
        return (ytd.get('rec_curr') or 0) + (ytd.get('units_curr') or 0)
    out['products'].sort(key=prod_sort_key, reverse=True)

    out_path = repo / args.out
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                        encoding='utf-8', newline='')
    print(f'\n-> {out_path} ({out_path.stat().st_size:,} bytes)')
    print(f'   Lineas con KPIs: {len(out["lines"])}')
    print(f'   Productos SIE en tabla: {len(out["products"])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
