#!/usr/bin/env python3
"""
shared/build-summary.py

Lee los data.js de cada linea (ya generados) y produce un solo
shared/cross-line-summary.json con los KPIs principales que el HUB
necesita mostrar como mini-tabla cross-linea.

El JSON resultante es chico (<10 KB) y se puede fetchear desde el
hub sin penalizar performance.

Uso:
    py shared/build-summary.py [--repo <ruta>]

Si no se pasa --repo, usa el directorio del script como ancla
(asume que el script vive en <repo>/shared/).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Lineas con data.js producido por build-data.ps1.
# (dermatologia tiene un placeholder, no genera data.js todavia.)
LINES = [
    {'key': 'cardio',       'label': 'Cardio Metabolismo', 'href': 'cardio/'},
    {'key': 'ATB',          'label': 'Antibioticos',       'href': 'ATB/'},
    {'key': 'OTC',          'label': 'OTC',                'href': 'OTC/'},
    {'key': 'mujer',        'label': 'Linea Mujer',        'href': 'mujer/'},
    {'key': 'respiratorio', 'label': 'Respiratorio',       'href': 'respiratorio/'},
    {'key': 'SNC',          'label': 'SNC / PSQ',          'href': 'SNC/'},
]


def _extract_window_assignments(text: str) -> dict:
    """Devuelve {VARIABLE_NAME: parsed_object} para cada window.X = {...}; en data.js."""
    out = {}
    pos = 0
    while True:
        m = re.search(r'window\.(\w+)\s*=\s*', text[pos:])
        if not m:
            break
        var_name = m.group(1)
        start_obj = pos + m.end()
        # Buscar primer { despues
        i = text.find('{', start_obj)
        if i < 0:
            break
        try:
            obj, end = json.JSONDecoder().raw_decode(text[i:])
            out[var_name] = obj
            pos = i + end
        except json.JSONDecodeError:
            pos = start_obj
            continue
    return out


def _summarize_line(repo: Path, line_key: str) -> dict:
    """Lee <line>/data.js si existe y extrae KPIs cross-linea."""
    data_js = repo / line_key / 'data.js'
    summary = {
        'hasData': False,
        'generatedAt': None,
        'budgetCut': None,
        'rxCut': None,
        'stockCut': None,
        'totalsYtdActual': None,
        'totalsYtdBudget': None,
        'compliance': None,
        'latestMonth': None,
        'latestActual': None,
        'familiesCount': None,
        'familiesWithPm': None,
    }
    if not data_js.is_file():
        return summary

    try:
        text = data_js.read_text(encoding='utf-8-sig', errors='replace')
    except Exception:
        return summary

    objs = _extract_window_assignments(text)
    # OTC_DATA suele tener summary; OTC_DASHBOARD suele tener mol_perf.
    data = objs.get('OTC_DATA') or {}
    dashboard = objs.get('OTC_DASHBOARD') or {}

    meta = data.get('meta') or dashboard.get('meta') or {}
    summary['hasData'] = True
    summary['generatedAt'] = meta.get('generatedAt') or None
    summary['budgetCut'] = meta.get('budgetCut') or None
    summary['rxCut'] = meta.get('rxCut') or None
    summary['stockCut'] = meta.get('stockCut') or None

    summ = data.get('summary') or {}
    totales = summ.get('Totales') or {}
    if totales:
        summary['totalsYtdActual'] = totales.get('ytdActual2026')
        summary['totalsYtdBudget'] = totales.get('ytdBudget2026')
        summary['latestMonth'] = totales.get('latestMonth')
        summary['latestActual'] = totales.get('latestActual')
        ya, yb = summary['totalsYtdActual'], summary['totalsYtdBudget']
        if isinstance(ya, (int, float)) and isinstance(yb, (int, float)) and yb:
            summary['compliance'] = round((ya / yb) * 100, 1)

    fams = data.get('families') or dashboard.get('families') or []
    if isinstance(fams, list):
        summary['familiesCount'] = len(fams)

    mp = dashboard.get('mol_perf') or data.get('mol_perf') or {}
    if isinstance(mp, dict):
        summary['familiesWithPm'] = sum(
            1 for f in mp
            if isinstance(mp[f], dict) and mp[f].get('products')
        )

    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(Path(__file__).resolve().parent.parent),
                    help='Raiz del repo (default: parent del script).')
    ap.add_argument('--out', default=None,
                    help='Output JSON path (default: <repo>/shared/cross-line-summary.json)')
    args = ap.parse_args()

    repo = Path(args.repo)
    out_path = Path(args.out) if args.out else (repo / 'shared' / 'cross-line-summary.json')

    summaries = []
    for ln in LINES:
        s = _summarize_line(repo, ln['key'])
        s.update({'key': ln['key'], 'label': ln['label'], 'href': ln['href']})
        summaries.append(s)
        flag = 'OK' if s['hasData'] else 'no-data'
        ya = s.get('totalsYtdActual')
        comp = s.get('compliance')
        ya_str = f"{ya:,}" if isinstance(ya, (int, float)) else '-'
        comp_str = f"{comp}%" if isinstance(comp, (int, float)) else '-'
        print(f"  {ln['key']:14} | {flag:8} | YTD={ya_str:>12} | comp={comp_str:>6} | {s.get('budgetCut') or '-'}")

    payload = {
        'generatedAt': repr(__import__('datetime').datetime.now().isoformat(timespec='seconds')).strip("'"),
        'lines': summaries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nWrote: {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
