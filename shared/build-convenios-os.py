# -*- coding: utf-8 -*-
"""Reconstruye D.convenios (por Obra Social) de las 7 lineas desde el extracto Qlik
de rofina (shared/qlik/rofina-extract-convenios-os.mjs, pivot "Detalle consumos y
aportes por convenio"). Ventana apples-vs-apples: mismo rango de meses en los dos
anios. Ver el docstring de OVERRIDES para el mapeo Producto->familia."""
# Alias Producto->familia por linea, para el grano por Obra Social de rofina.
# Se ordenan por LONGITUD DE PATRON desc: el especifico gana sobre el base
# ('METGLUCON DUO' antes que 'METGLUCON', 'ISIS MINI 24' antes que 'ISIS').
# '__IGNORE__' descarta productos que no pertenecen a ninguna familia del tablero
# (ISIS NAT no tiene segmento en el manifest; sin esto caeria en ALTA DOSIS).
OVERRIDES = {
    'cardio': {
        'METGLUCON DUO': ['METGLUCON DUO'],
        'METGLUCON AP': ['METGLUCON'],          # el resto de METGLUCON es AP
    },
    'respiratorio': {
        'DUO-DECADRON': ['DUODECADRON'],        # en Qlik va sin guion ni espacio
        'HEXALER BRONQUIAL DU': ['HEXALER BRONQ DUO'],
        'HEXALER BRONQUIAL': ['HEXALER BRONQUIAL'],
    },
    'mujer': {   # familias = segmentos de marketing (segmentToFams del manifest)
        'SIN ESTROGENO': ['ISIS FREE'],
        'BAJA DOSIS 24': ['ISIS MINI 24'],
        'BAJA DOSIS 21+7': ['ISIS MINI'],
        'ALTA DOSIS': ['ISIS'],
        'COMPLEX': ['SIDERBLUT COMPLEX', 'SIDERBLUT FOLIC'],
        'SOLO': ['SIDERBLUT', 'FERINSOL'],
        'D3 PLUS': ['TRIP D3 PLUS'],
        'D3': ['TRIP D3'],
        'BASE D': ['CALCIO BASE DUPOMAR D', 'CALCIO CITRATO DUPOMAR D3'],
        'BASE': ['CALCIO BASE DUPOMAR'],
        'DELTROX': ['DELTROX'],
        'CLIMATIX': ['CLIMATIX'],
        '__IGNORE__': ['ISIS NAT'],
    },
}

import json, re, sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(r'C:\Users\camarinaro\Marcas-CardioMetabolismo')
# Carpeta con los os_<anio>.json de rofina-extract-convenios-os.mjs.
# Default: shared/qlik del repo; se puede pasar con --dir <ruta>.
SP = Path(sys.argv[sys.argv.index('--dir') + 1]) if '--dir' in sys.argv else REPO / 'shared' / 'qlik'
LINES = ['cardio', 'ATB', 'OTC', 'respiratorio', 'mujer', 'SNC', 'dermatologia']
MANI = json.loads((REPO / 'shared' / 'close-manifest.json').read_text(encoding='utf-8'))
MINBASE = ((MANI.get('convenios') or {}).get('dermato') or {}).get('minBaseForDelta', 5)
DERMA_ALIAS = [(a[0], a[1]) for a in
               ((MANI.get('convenios') or {}).get('dermato') or {}).get('productAliases', [])]


def oskey(s):
    m = re.search(r'\((\d{3,6})\)', str(s))
    return m.group(1) if m else re.sub(r'\s+', ' ', str(s).strip().upper())


def fam_of(prod, alias):
    u = str(prod).upper()
    for fam, al in alias:
        if al.upper() in u:
            return fam
    return None


MES_ES = {'Jan': 'Ene', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Abr', 'May': 'May',
          'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago', 'Sep': 'Sep', 'Oct': 'Oct',
          'Nov': 'Nov', 'Dec': 'Dic'}
ORD = list(MES_ES)


def load_year(y):
    """filas + los meses que la extraccion VERIFICO aplicados (no los pedidos)."""
    d = json.loads((SP / f'os_{y}.json').read_text(encoding='utf-8'))
    return d['rows'], list(d.get('mesesAplicados') or d.get('months') or [])


def periodo(meses):
    """('Ene-Jun', '1er semestre') a partir de los meses aplicados. El rotulo se
    DERIVA del dato: si cambia la ventana, los titulos del tablero cambian solos."""
    i = sorted(ORD.index(m) for m in meses if m in ORD)
    if not i:
        return '', ''
    if i != list(range(i[0], i[-1] + 1)):          # ventana no contigua
        return ', '.join(MES_ES[ORD[x]] for x in i), '%d meses' % len(i)
    rango = MES_ES[ORD[i[0]]] if len(i) == 1 else MES_ES[ORD[i[0]]] + '–' + MES_ES[ORD[i[-1]]]
    n = len(i)
    if n == 12:
        tipo = 'año cerrado'
    elif n == 6:
        tipo = '1er semestre' if i[0] == 0 else ('2do semestre' if i[0] == 6 else '6 meses')
    elif n == 3 and i[0] % 3 == 0:
        tipo = 'Q%d' % (i[0] // 3 + 1)
    elif n == 1:
        tipo = 'mes'
    else:
        tipo = '%d meses' % n
    return rango, tipo


def agg(rows, alias):
    out = defaultdict(lambda: defaultdict(float)); disp = {}
    for os1, prod, val in rows:
        if not prod or str(prod).strip() in ('Totales', '-'):
            continue
        if not os1 or str(os1).strip() == 'Totales':
            continue
        f = fam_of(prod, alias)
        if not f:
            continue
        k = oskey(os1)
        out[f][k] += (val or 0)
        disp[(f, k)] = os1
    return out, disp


def blk(text, anchor):
    m = re.search(re.escape(anchor) + r'\s*=\s*', text)
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    return D, ob, end


# La medida extraida es sum(Consumo_Unidades_Inf): el consumo BRUTO, la misma que
# usa el "% convenio UNI" del tablero de Rofina. NO son unidades netas de notas de
# debito. Medido contra el resto del tablero en las 82 familias comparables de las 7
# lineas, corre ~21% arriba del neto (mediana 1,21; p25 1,17 / p75 1,23; sigma 0,079).
# Se rotula en la pagina para que nadie lo lea como unidades vendidas.
METRICA = 'consumo bruto por convenio (antes de notas de débito)'
METRICA_TIP = ('Medida del tablero de Rofina (Consumo_Unidades_Inf), la misma que usa '
               'el % convenio UNI. Es BRUTA: medida en 09/2026 corre ~21% arriba de '
               'las unidades netas de notas de débito.')

r26, m26 = load_year(2026)
r25, m25 = load_year(2025)
if sorted(m26) != sorted(m25):
    sys.exit('ABORTA: ventanas distintas -> 2026=%s vs 2025=%s (no es apples vs apples)' % (m26, m25))
PER, TIPO = periodo(m26)
if not PER:
    sys.exit('ABORTA: los extractos no declaran mesesAplicados; no se puede rotular el periodo')
print('periodo comparado: %s (%s)  2026 vs 2025' % (PER, TIPO))

check = '--check' in sys.argv
tot_upd = tot_keep = 0

for line in LINES:
    p = REPO / line / 'data.js'
    text = p.read_text(encoding='utf-8', errors='replace')
    D, ob, end = blk(text, 'window.OTC_DASHBOARD')
    old = D.get('convenios')
    if not isinstance(old, dict) or not old:
        print(f'{line:14} sin clave convenios -> skip'); continue
    if line == 'dermatologia':
        alias = DERMA_ALIAS
    else:
        ov = OVERRIDES.get(line, {})
        pares = []
        for f in list(old.keys()) + [k for k in ov if k.startswith('__')]:
            for pat in ov.get(f, [f]):
                pares.append((f, pat))
        # el patron MAS LARGO gana: 'METGLUCON DUO' antes que 'METGLUCON'
        alias = sorted(pares, key=lambda x: len(x[1]), reverse=True)
    a26, d26 = agg(r26, alias)
    a25, d25 = agg(r25, alias)
    new, kept = {}, []
    for fam in old:
        if fam.startswith('__'):
            continue
        cur, prev = a26.get(fam, {}), a25.get(fam, {})
        if not cur and not prev:
            new[fam] = old[fam]; kept.append(fam); continue
        rows = []
        for k in set(cur) | set(prev):
            u, u25 = round(cur.get(k, 0)), round(prev.get(k, 0))
            if u == 0 and u25 == 0:
                continue
            dl = round((u - u25) / u25 * 100, 1) if u25 >= MINBASE else None
            rows.append({'os': d26.get((fam, k)) or d25.get((fam, k)),
                         'unid': u, 'unid24': u25, 'delta': dl})
        rows.sort(key=lambda x: (-(x['unid'] or 0), -(x['unid24'] or 0), str(x['os'])))
        new[fam] = rows if rows else old[fam]
        if not rows:
            kept.append(fam)
    upd = len(new) - len(kept)
    tot_upd += upd; tot_keep += len(kept)
    s26 = sum(r['unid'] for f in new if f not in kept for r in new[f])
    s25 = sum(r['unid24'] for f in new if f not in kept for r in new[f])
    print(f'{line:14} familias={len(new):3}  actualizadas={upd:3}  conservadas={len(kept):2} '
          f'{"(" + ", ".join(kept[:3]) + ")" if kept else ""}   2026={s26:,}  2025={s25:,}')
    if not check:
        D['convenios'] = new
        D.setdefault('meta', {}).update({
            'conv_current_year': '2026', 'conv_prev_year': '2025',
            'conv_period': PER, 'conv_period_kind': TIPO,
            'conv_metric': METRICA, 'conv_metric_tip': METRICA_TIP})
        out = text[:ob] + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + text[ob + end:]
        p.write_text(out, encoding='utf-8', newline='')

print(f'\nTOTAL: {tot_upd} familias actualizadas, {tot_keep} conservadas (sin match en Qlik)')
print('MODO CHECK (no se escribio nada)' if check else 'escrito en los data.js')
