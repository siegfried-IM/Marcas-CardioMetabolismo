#!/usr/bin/env python3
"""
shared/apply-sidebar-layout.py

Aplica el nuevo layout a todas las lineas del repo:
  - Linea KPIs en bloque con border rojo + titulo 'LÍNEA · <NAME>'
  - Filtro de marca como SIDEBAR FIXED (position:fixed, right:16px,
    top:80px, ancho 250px, siempre visible al hacer scroll).
  - Brand KPIs en bloque con border violeta + titulo prominente
    'MARCA · <BRAND>' cuando hay filtro activo.

Aplica a: cardio, ATB, OTC, respiratorio, mujer, SNC, dermato

NO modifica el JS de cada linea ni la data. Solo HTML + CSS.

Uso: py shared/apply-sidebar-layout.py [--dry-run]
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

LINES = [
    ('cardio',  'cardio/index.html',                       'Cardio Metabolismo'),
    ('antibio', 'ATB/index.html',                          'Antibióticos'),
    ('OTC',     'OTC/index.html',                          'OTC'),
    ('respi',   'respiratorio/index.html',                 'Respiratoria'),
    ('mujer',   'mujer/index.html',                        'Mujer'),
    ('SNC',     'SNC/index.html',                          'S.N.C.'),
    ('dermato', 'dermatologia/dermato_dashboard.html',     'Dermatología'),
]


def transform(text, line_name):
    # 1) Update .wrap CSS to add padding-right: 280px
    text = re.sub(
        r'\.wrap\{max-width:1200px;margin:0 auto;padding:32px 24px 80px;\}',
        '.wrap{max-width:1200px;margin:0 auto;padding:32px 280px 80px 24px;}',
        text, count=1
    )

    # 2) Reemplazar patron general (period toggle + s-kpi + global-filter-bar + brand-kpi-section)
    # Para dermato (que tiene grid layout custom de mi commit anterior) y para
    # los otros 6 (estructura legacy), buscamos cualquiera.

    # Patron legacy: <div style="display:flex...">Ver período... <div class="kpi-row" id="s-kpi">... <div id="global-filter-bar"...> ... <div id="brand-kpi-section"...> ...
    legacy_pattern = re.compile(
        r'(\s*<!-- GLOBAL BRAND FILTER -->\s*\n'
        r'\s*<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">\s*\n'
        r'\s*<span[^>]*>Ver período:</span>\s*\n'
        r'\s*(<div class="kpi-toggle">.*?</div>)\s*\n'
        r'\s*</div>\s*\n'
        r'\s*<div class="kpi-row" id="s-kpi"></div>\s*\n'
        r'\s*<div id="global-filter-bar"[^>]*>.*?</div>\s*\n\s*</div>\s*\n'
        r'\s*\n?\s*<!-- BRAND KPI STRIP -->\s*\n'
        r'\s*<div id="brand-kpi-section"[^>]*>.*?</div>\s*\n\s*</div>)',
        re.DOTALL
    )

    new_block = build_new_block(line_name)

    new_text, n = legacy_pattern.subn(new_block, text)
    if n > 0:
        return new_text, 'legacy', n

    # Patron dermato (post-commit cf8f94e): line-vs-filter grid + line-block + filter-side + brand-kpi-section
    dermato_pattern = re.compile(
        r'\s*<!-- ═══ LAYOUT: Linea KPIs.*?<!-- KPI TOGGLE \+ STRIP -->',
        re.DOTALL
    )
    new_text2, n2 = dermato_pattern.subn(new_block + '\n\n  <!-- KPI TOGGLE + STRIP -->', text)
    if n2 > 0:
        return new_text2, 'dermato', n2

    return text, 'no-match', 0


def build_new_block(line_name):
    """Devuelve el HTML reemplazo unificado."""
    return r"""
  <!-- ═══ LÍNEA + MARCA + FILTRO SIDEBAR ═══ -->
  <!-- LÍNEA: bloque con border rojo, KPIs full-width -->
  <div class="line-block" style="border:2px solid #b01e1e;border-radius:12px;padding:16px 18px 18px;background:#fff;margin-bottom:20px;">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:700;color:#b01e1e;letter-spacing:.2em;text-transform:uppercase;">●</span>
        <span style="font-family:'IBM Plex Sans',sans-serif;font-size:14px;font-weight:800;color:#111827;letter-spacing:-.01em;">Línea · """ + line_name + r"""</span>
        <span style="font-size:10px;color:#4b5563;">— performance global</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:10px;color:#4b5563;">Período:</span>
        <div class="kpi-toggle">
          <button class="kt-btn on" id="kpi-ytd-label" onclick="setKpiPeriod('ytd')">YTD</button>
          <button class="kt-btn" id="kpi-mat-label" onclick="setKpiPeriod('mat')">MAT</button>
        </div>
      </div>
    </div>
    <div class="kpi-row" id="s-kpi"></div>
  </div>

  <!-- MARCA: bloque con border violeta, aparece al filtrar marca -->
  <div id="brand-kpi-section" style="display:none;margin-bottom:24px;border:2px solid #7c3aed;border-radius:12px;padding:16px 18px 18px;background:linear-gradient(180deg,#faf5ff,#fff);">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
      <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:700;color:#7c3aed;letter-spacing:.2em;text-transform:uppercase;">▼ Marca seleccionada</span>
      <span id="brand-kpi-label" style="font-family:'IBM Plex Sans',sans-serif;font-size:18px;font-weight:800;color:#111827;letter-spacing:-.02em;"></span>
      <span style="font-size:10px;color:#4b5563;margin-left:auto;" id="brand-kpi-period-label"></span>
    </div>
    <div class="kpi-row" id="s-brand-kpi"></div>
  </div>

  <!-- FILTRO de Marca: SIDEBAR FIXED siempre visible al hacer scroll -->
  <div id="global-filter-bar" style="position:fixed;right:16px;top:80px;width:240px;max-height:calc(100vh - 100px);overflow-y:auto;border:1px solid rgba(176,30,30,.25);border-radius:12px;padding:14px 16px;background:rgba(255,255,255,.96);backdrop-filter:blur(8px);box-shadow:0 4px 16px rgba(0,0,0,.08);z-index:50;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
      <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:700;color:#b01e1e;letter-spacing:.2em;text-transform:uppercase;">Filtro · Marca</span>
    </div>
    <span style="font-size:10px;color:#4b5563;display:block;margin-bottom:12px;line-height:1.4;">Seleccioná una marca para sincronizar todas las secciones.</span>
    <div class="pill-group" id="global-pills"></div>
    <button onclick="clearGlobalFilter()" id="clear-filter-btn" style="display:none;margin-top:12px;padding:6px 10px;border-radius:6px;border:1px solid rgba(239,68,68,.3);background:rgba(239,68,68,.07);color:var(--red);font-size:10px;cursor:pointer;font-family:'IBM Plex Sans',sans-serif;transition:all .2s;width:100%;">✕ Limpiar filtro</button>
  </div>

  <!-- Mobile: stack y filter inline cuando viewport pequenio -->
  <style>
    @media (max-width: 1100px) {
      .wrap { padding-right: 24px !important; }
      #global-filter-bar { position: relative !important; right: auto !important; top: auto !important; width: 100% !important; max-height: none !important; margin-bottom: 24px !important; }
    }
  </style>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    n_ok = 0
    for key, rel, name in LINES:
        p = REPO / rel
        if not p.is_file():
            print(f'  [{key}] SKIP: no existe'); continue
        text = p.read_text(encoding='utf-8', errors='replace')
        new_text, kind, n = transform(text, name)
        if n == 0:
            print(f'  [{key}] WARN: pattern no matched (kind={kind})')
            continue
        if args.dry_run:
            print(f'  [{key}] DRY: matched {kind} (n={n})')
        else:
            p.write_text(new_text, encoding='utf-8', newline='')
            print(f'  [{key}] OK ({kind}, {p.stat().st_size:,} bytes)')
        n_ok += 1
    print(f'\nTotal: {n_ok}/{len(LINES)} lineas updated')
    return 0


if __name__ == '__main__':
    sys.exit(main())
