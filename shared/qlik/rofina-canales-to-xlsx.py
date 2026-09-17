# -*- coding: utf-8 -*-
"""Arma el xlsx por trimestre que lee shared/build-canales-quarterly.py, desde los
JSON de shared/qlik/rofina-extract-canales.mjs.

El % que escribe es NETO DE BAJAS:

    % convenio  = consumo neto de ND / unidades facturadas
    % mostrador = 1 - % convenio

y NO el del pivot ThZZvT de rofina, que divide el consumo BRUTO (sin descontar las
bajas) por las unidades facturadas y por eso pasa de 100 %: DILATREND Q1-2026 daba
111,3 % (185.411 consumidas contra 166.567 facturadas). Con el neto da 84,7 %.
La decision la tomo Carlos el 2026-09-17; rofina ya habia migrado su propio KPI.

Uso: py shared/qlik/rofina-canales-to-xlsx.py --dir <carpeta con can_*.json> --out <carpeta destino>
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

QN = {'Q1': '1er', 'Q2': '2do', 'Q3': '3er', 'Q4': '4to'}
HDR = ['Laboratorio', 'Familia', 'Producto', 'Unidades facturadas',
       'Consumo uni', '% convenio UNI', '% mostrador UNI']


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='carpeta con can_<AAAA><Qn>.json')
    ap.add_argument('--out', required=True, help='carpeta destino de los xlsx')
    ap.add_argument('--fecha', default='17 de septiembre de 2026')
    ap.add_argument('--solo', default='', help='lista AAAAQn separada por comas')
    a = ap.parse_args()
    from openpyxl import Workbook

    src, dst = Path(a.dir), Path(a.out)
    solo = {x.strip() for x in a.solo.split(',') if x.strip()}
    hechos = 0
    for f in sorted(src.glob('can_*.json')):
        m = re.fullmatch(r'can_(\d{4})(Q[1-4])', f.stem)
        if not m:
            continue                      # los controles (_ANIO, _H1) no son trimestres
        year, q = m.group(1), m.group(2)
        if solo and (year + q) not in solo:
            continue
        d = json.loads(f.read_text(encoding='utf-8'))
        wb = Workbook(write_only=True)
        ws = wb.create_sheet('Hoja1')
        ws.append(HDR)
        n = 0
        for fam, fact, bruto, neto in d['rows']:
            if not fam or str(fam).strip().lower() in ('totales', 'total'):
                continue
            # Sin base facturada el cociente no significa nada. Se escribe 0/0 y
            # build-canales-quarterly lo marca 'base' mirando el facturado (descarta
            # los % de esa rama, no los publica). Van 0 y no None a proposito: openpyxl
            # RECORTA las celdas None del final de la fila y el lector indexa por
            # posicion -> IndexError. Mismo caso que shared/build-stock-from-laboratorio.
            if not fact or fact <= 0:
                c = m_ = 0
            else:
                c = neto / fact
                m_ = 1 - c
            ws.append(['Siegfried S.A.', fam, 'Totales', round(fact or 0),
                       round(neto or 0), c, m_])
            n += 1
        nombre = (f'Convenios vs mostrador (neto) - {a.fecha} '
                  f'{QN[q]} trimestre {year}.xlsx')
        wb.save(dst / nombre)
        print(f'  {year} {q}: {n} familias -> {nombre}')
        hechos += 1
    print(f'{hechos} trimestres escritos en {dst}')
    return 0 if hechos else 1


if __name__ == '__main__':
    sys.exit(main())
