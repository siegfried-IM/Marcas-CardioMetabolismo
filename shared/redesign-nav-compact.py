"""Reorganiza la barra de navegacion (top-bar) de las 7 lineas para que entre
en una sola fila sin scroll horizontal.

Cambios:
1. Saca el <img> inline (base64, ~256KB cada uno) duplicado al final del nav.
2. Agrupa los tabs externos (Precios/DDD/Competidores/Bonos PAP) + nav-ext "Hub"
   dentro de un nuevo <div class="nav-actions"> que se ancla a la derecha
   (margin-left:auto). Asi los items de seccion quedan a la izquierda y las
   acciones (Excel/PDF/Datos que se inyectan por JS) caen siempre al lado derecho.
3. Ajusta CSS:
   - .nav-item: padding 0 9px (era 14), font 10.5px (era 11)
   - .nav-tab.hl: pill mas chico (padding 0 10, height 28, font 10.5)
   - .nav-items: sin overflow-x:auto (el ancho lo absorbe nav-actions)
   - .nav-actions: nuevo, margin-left:auto, flex, gap 5px
   - .nav-back / .nav-ext: padding mas chico

No toca otras secciones, ni los scripts (export-pdf.js, data-status.js, export.js)
que siguen funcionando porque mantenemos el anchor .nav-ext[href].
Idempotente.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGETS = [
    'cardio/index.html',
    'ATB/index.html',
    'OTC/index.html',
    'respiratorio/index.html',
    'SNC/index.html',
    'mujer/index.html',
    'dermatologia/dermato_dashboard.html',
]


# === Nuevos estilos CSS ===
NEW_CSS = """.nav-logo{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;
  color:#b01e1e;letter-spacing:.18em;margin-right:12px;white-space:nowrap;
  text-decoration:none;display:inline-flex;align-items:center;gap:6px;
  padding:4px 6px;border-radius:6px;transition:background .15s;flex-shrink:0;}
.nav-logo:hover{background:rgba(176,30,30,.08);}
.nav-back{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;
  color:#b01e1e;letter-spacing:.12em;text-transform:uppercase;text-decoration:none;
  border:1px solid rgba(176,30,30,.3);border-radius:6px;padding:5px 10px;
  margin-right:10px;white-space:nowrap;transition:all .15s;display:inline-flex;align-items:center;gap:6px;flex-shrink:0;}
.nav-back:hover{background:#b01e1e;color:#fff;border-color:#b01e1e;}
.nav-items{display:flex;flex:1 1 auto;min-width:0;overflow-x:auto;scrollbar-width:none;}
.nav-items::-webkit-scrollbar{display:none;}
.nav-item{height:48px;padding:0 9px;display:flex;align-items:center;
  font-size:10.5px;font-weight:500;color:#4b5563;cursor:pointer;
  border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;text-decoration:none;}
.nav-item:hover{color:var(--text);}
.nav-item.on{color:#b01e1e;border-bottom-color:#b01e1e;}
.nav-actions{display:flex;align-items:center;gap:5px;margin-left:auto;flex-shrink:0;padding-left:8px;}
.nav-actions .nav-tab{font-family:'IBM Plex Sans',sans-serif;font-size:10.5px;font-weight:700;
  letter-spacing:.04em;text-decoration:none;display:inline-flex;align-items:center;
  height:28px;padding:0 10px;border-radius:5px;white-space:nowrap;transition:filter .15s;}
.nav-actions .nav-tab:hover{filter:brightness(1.08);}
.nav-ext{font-size:10px;color:#4b5563;text-decoration:none;
  padding:5px 10px;border:1px solid var(--border);border-radius:5px;
  white-space:nowrap;transition:all .2s;flex-shrink:0;font-family:'IBM Plex Mono',monospace;font-weight:700;letter-spacing:.04em;}
.nav-ext:hover{color:#b01e1e;border-color:rgba(176,30,30,.5);}
.data-status-badge{margin-left:0 !important;}"""


def parse_nav(nav_inner):
    """Extract components from current nav inner HTML."""
    # nav-back (Hub button at start)
    m_back = re.search(r'<a class="nav-back"[^>]*>.*?</a>', nav_inner, re.DOTALL)
    nav_back = m_back.group(0) if m_back else ''

    # nav-logo (Siegfried red logo)
    m_logo = re.search(r'<a class="nav-logo"[^>]*>.*?</a>', nav_inner, re.DOTALL)
    nav_logo = m_logo.group(0) if m_logo else ''

    # nav-items inner: only section nav items with href="#..."
    section_items = re.findall(r'<a class="nav-item(?:\s+on)?" href="#[^"]*"[^>]*>.*?</a>', nav_inner, re.DOTALL)

    # Right-side pill tabs: nav-tab.hl OR nav-item with inline background style
    # (mujer uses nav-item with inline style for DDD/Comp)
    tab_tags = re.findall(
        r'<a class="nav-tab hl"[^>]*>.*?</a>'
        r'|<a class="nav-item" href="\./DDD/index\.html"[^>]*>.*?</a>'
        r'|<a class="nav-item" href="\./DDD/competidores\.html"[^>]*>.*?</a>',
        nav_inner, re.DOTALL
    )

    # nav-ext: extract href (defaults to "../")
    m_ext = re.search(r'<a class="nav-ext"\s+href="([^"]*)"[^>]*>.*?</a>', nav_inner, re.DOTALL)
    ext_href = m_ext.group(1) if m_ext else '../'

    return nav_back, nav_logo, section_items, tab_tags, ext_href


def normalize_pill_style(tag):
    """Normalize a pill tab's inline style to the new size (height 28, padding 0 10)."""
    # Remove old size attributes from inline style, keep colors
    tag = re.sub(r'height:\s*\d+px;?', '', tag)
    tag = re.sub(r'padding:\s*\d+\s+\d+px;?', '', tag)
    tag = re.sub(r'padding:\s*0\s+\d+px;?', '', tag)
    tag = re.sub(r'margin:\s*[^;"]+;?', '', tag)
    tag = re.sub(r'border-radius:\s*\d+px;?', '', tag)
    tag = re.sub(r'font-weight:\s*\d+;?', '', tag)
    # Make nav-item-styled buttons (mujer) into nav-tab styled
    tag = tag.replace('class="nav-item"', 'class="nav-tab"')
    tag = tag.replace('class="nav-tab hl"', 'class="nav-tab"')
    # Clean up double spaces in style
    tag = re.sub(r'style="\s*([^"]*?)\s*"', lambda m: f'style="{re.sub(chr(32)+chr(32)+"+", chr(32), m.group(1)).strip()}"', tag)
    return tag


def build_new_nav(nav_back, nav_logo, section_items, tab_tags, ext_href):
    """Build the new clean nav HTML."""
    sections_html = '\n    '.join(section_items)
    tabs_html = '\n    '.join(normalize_pill_style(t) for t in tab_tags)
    return f"""
  {nav_back}
  {nav_logo}
  <div class="nav-items">
    {sections_html}
  </div>
  <div class="nav-actions">
    {tabs_html}
    <a class="nav-ext" href="{ext_href}">← Hub</a>
  </div>
"""


def patch_css(t):
    """Replace existing nav CSS rules with new compact version."""
    # The CSS block to replace: from `.nav-logo{` to end of `.nav-ext:hover{...}`
    # Mark: starts with `.nav-logo{font-family:'IBM Plex Mono'`
    # Ends after `.nav-ext:hover{color:#b01e1e;border-color:rgba(176,30,30,.5);}`
    pat = re.compile(
        r"\.nav-logo\{font-family:'IBM Plex Mono'.*?\.nav-ext:hover\{color:#b01e1e;border-color:rgba\(176,30,30,\.5\);\}"
        r"(?:\s*\.data-status-badge\{margin-left:0\s*!important;\})*",
        re.DOTALL,
    )
    m = pat.search(t)
    if not m:
        return t, False, 'css-not-found'
    if m.group(0).strip() == NEW_CSS.strip():
        return t, False, 'css-already-applied'
    return t[:m.start()] + NEW_CSS + t[m.end():], True, 'css-updated'


def patch_nav(t):
    """Replace nav block with restructured version."""
    pat = re.compile(r'<nav class="nav">(.*?)</nav>', re.DOTALL)
    m = pat.search(t)
    if not m:
        return t, False, 'nav-not-found'
    nav_inner = m.group(1)
    # Idempotency: if nav-actions already present, skip
    if 'class="nav-actions"' in nav_inner:
        return t, False, 'nav-already-restructured'

    nav_back, nav_logo, section_items, tab_tags, ext_href = parse_nav(nav_inner)
    if not section_items:
        return t, False, 'no-section-items'

    new_inner = build_new_nav(nav_back, nav_logo, section_items, tab_tags, ext_href)
    new_nav = f'<nav class="nav">{new_inner}</nav>'
    return t[:m.start()] + new_nav + t[m.end():], True, 'nav-restructured'


def patch_file(path):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')
    t1, css_changed, css_status = patch_css(t)
    t2, nav_changed, nav_status = patch_nav(t1)
    if not css_changed and not nav_changed:
        return f'no-op ({css_status}, {nav_status})'
    p.write_text(t2, encoding='utf-8', newline='')
    return f'OK ({css_status}, {nav_status})'


def main():
    for f in TARGETS:
        print(f'  {f}: {patch_file(f)}')


if __name__ == '__main__':
    main()
