#!/usr/bin/env python3
"""
shared/trim-mujer-stock.py

One-shot: limita la data de stock de mujer a 2025+2026, eliminando todo
lo de 2022/2023/2024 que estaba "rellenando" el chart sin aportar.

Cambios in-place en mujer/index.html (dentro de `const D = {...};`):
  - D.stock[F][month]: borra entries con year < 2025
  - D.stock_alerts[F].ventas/dias/statuses: trim a las posiciones de
    months >= Ene 2025. alert_indices se re-indexa al nuevo array.
    n_alerts se recalcula. worst_status se mantiene (escalar).
  - D.stock_pres[P]: idem que stock_alerts.

Asume que stock_alerts/stock_pres tenian arrays alineados con los ultimos
24 meses del stock (May 2024 - Apr 2026). Recortamos a los ultimos 16
(Ene 2025 - Apr 2026).

NO toca otras secciones (precios, recetas, mol_perf, budget, etc.).
NO toca otras lineas.
"""

from __future__ import annotations
import json, re, sys
from pathlib import Path

CUTOFF_YEAR = 2025  # mantener solo year >= CUTOFF_YEAR

MES_EN = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
MES_TO_INT = {v:k for k,v in MES_EN.items()}


def month_year(month_key_en):
    parts = str(month_key_en).split()
    if len(parts) != 2: return None
    return parts[0], int(parts[1])


def month_sort(month_key_en):
    p = month_year(month_key_en)
    if not p: return 0
    return p[1]*100 + MES_TO_INT.get(p[0], 0)


def main():
    p = Path(r'C:\Users\camarinaro\Marcas-CardioMetabolismo\mujer\index.html')
    text = p.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D = (\{)', text)
    if not m:
        print('ERROR: no encontre const D ='); return 2
    obj_start = m.start() + len('const D = ')
    obj_start = text.index('{', obj_start)
    D, end = json.JSONDecoder().raw_decode(text[obj_start:])
    abs_end = obj_start + end

    # 1) Trim D.stock[F]: drop months < CUTOFF_YEAR
    stock = D.get('stock', {})
    families_with_changes = 0
    months_dropped_total = 0
    for fam, months_dict in list(stock.items()):
        if not isinstance(months_dict, dict): continue
        before = len(months_dict)
        for k in list(months_dict.keys()):
            yr = month_year(k)
            if yr and yr[1] < CUTOFF_YEAR:
                del months_dict[k]
        after = len(months_dict)
        if before != after:
            families_with_changes += 1
            months_dropped_total += (before - after)
    print(f'stock: {families_with_changes} familias modificadas, {months_dropped_total} entries borradas total')

    # 2) Trim arrays in stock_alerts y stock_pres. Asumimos que el array es
    #    la ventana de los ULTIMOS N meses del stock para cada familia/pres.
    #    Por lo tanto, los meses asociados a cada posicion del array son
    #    "ultimos N meses ordenados". Sea N el len del array. Si los ultimos
    #    N meses del stock contienen K meses con year < CUTOFF, dropeamos los
    #    primeros K elementos del array.
    def trim_array_obj(obj, fam_months_sorted_desc, label):
        """obj tiene ventas/dias/statuses/alert_indices/worst_status/n_alerts.
           fam_months_sorted_desc = lista del stock ordenada DESCENDENTE para
           identificar las posiciones de cada slot."""
        n = len(obj.get('ventas', [])) if isinstance(obj.get('ventas'), list) else 0
        if n == 0: return False
        # Los ultimos n meses ordenados ASC del stock historico:
        # tomamos los ultimos n meses (incluyendo los que ya borramos) -- pero
        # como ya borramos, fam_months_sorted_desc es el stock POST-trim.
        # Mejor: reconstruir ventana con meses pre-trim. Como NO los tenemos,
        # asumimos que el array len corresponde a los ultimos n meses MIXED
        # (incluyendo pre-2025). Si todos los meses post-trim son menos que n,
        # tenemos que dropear los primeros (n - len_post_trim) entries del array.
        post_trim_len = len(fam_months_sorted_desc)
        if post_trim_len >= n:
            # Hay tantos o mas meses post-trim que el len del array, no hay que dropear
            return False
        drop = n - post_trim_len
        for k in ('ventas', 'dias', 'statuses'):
            v = obj.get(k)
            if isinstance(v, list) and len(v) >= drop:
                obj[k] = v[drop:]
        # alert_indices: filtrar y re-indexar
        ai = obj.get('alert_indices')
        if isinstance(ai, list):
            new_ai = [i - drop for i in ai if isinstance(i, int) and i >= drop]
            obj['alert_indices'] = new_ai
            obj['n_alerts'] = len(new_ai)
            # worst_status puede ser stale; lo dejamos
        return True

    sa = D.get('stock_alerts', {})
    fam_changed = 0
    for fam, obj in sa.items():
        if not isinstance(obj, dict): continue
        # Lista de meses post-trim de la familia, sorted ASC
        fam_months = sorted(stock.get(fam, {}).keys(), key=month_sort)
        if trim_array_obj(obj, fam_months, fam):
            fam_changed += 1
    print(f'stock_alerts: {fam_changed} familias trimmed')

    sp = D.get('stock_pres', {})
    pres_changed = 0
    for pres, obj in sp.items():
        if not isinstance(obj, dict): continue
        # stock_pres tiene 'familia' que apunta a la familia; usamos sus meses
        fam = obj.get('familia')
        fam_months = sorted(stock.get(fam, {}).keys(), key=month_sort) if fam else []
        if trim_array_obj(obj, fam_months, pres):
            pres_changed += 1
    print(f'stock_pres: {pres_changed} presentaciones trimmed')

    new_text = text[:obj_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]
    p.write_text(new_text, encoding='utf-8', newline='')
    print(f'\n-> {p} reescrito ({p.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
