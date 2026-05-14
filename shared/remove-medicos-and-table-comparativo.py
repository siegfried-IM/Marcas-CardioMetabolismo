"""Saca Medicos de Recetas y convierte Comparativo en tabla (7 lineas).
Esta version busca la SEGUNDA innerHTML de rec-detail (la del Comparativo,
no la fallback) usando un anchor de comienzo distintivo.

Idempotente: si ya fue aplicado (SF_COMPARATIVO_TABLE marker), skip.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

NEW_BLOCK = """// SF_COMPARATIVO_TABLE
  document.getElementById('rec-detail').innerHTML=`
    <p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">Comparativo</p>
    <table style="width:100%;border-collapse:collapse;font-size:11px;font-family:'IBM Plex Mono',monospace;">
      <thead><tr style="border-bottom:1px solid rgba(0,0,0,.1);">
        <th style="text-align:left;padding:4px 6px;font-weight:700;color:#6b7280;font-size:9px;letter-spacing:.08em;text-transform:uppercase;">Métrica</th>
        <th style="text-align:right;padding:4px 6px;font-weight:700;color:#6b7280;font-size:9px;letter-spacing:.08em;text-transform:uppercase;">${fmtRecLabel(prevYearMes)||'—'}</th>
        <th style="text-align:right;padding:4px 6px;font-weight:700;color:#6b7280;font-size:9px;letter-spacing:.08em;text-transform:uppercase;">${fmtRecLabel(lastMes)||'—'}</th>
        <th style="text-align:right;padding:4px 6px;font-weight:700;color:#6b7280;font-size:9px;letter-spacing:.08em;text-transform:uppercase;">Δ</th>
      </tr></thead>
      <tbody>
        <tr style="border-bottom:1px solid rgba(0,0,0,.04);">
          <td style="padding:6px;color:#4b5563;">Recetas</td>
          <td style="padding:6px;text-align:right;font-weight:600;color:#111827;">${prevData.recetas!=null?prevData.recetas.toLocaleString('es-AR'):'—'}</td>
          <td style="padding:6px;text-align:right;font-weight:700;color:#111827;">${lastData.recetas!=null?lastData.recetas.toLocaleString('es-AR'):'—'}</td>
          <td style="padding:6px;text-align:right;font-weight:600;color:${recDelta==null?'#9ca3af':recDelta>=0?'#16a34a':'#dc2626'}">${recDelta!=null?(recDelta>=0?'+':'')+recDelta+'%':'—'}</td>
        </tr>
        <tr>
          <td style="padding:6px;color:#4b5563;">MS%</td>
          <td style="padding:6px;text-align:right;font-weight:600;color:#111827;">${msPrev!=null?msPrev.toFixed(2)+'%':'—'}</td>
          <td style="padding:6px;text-align:right;font-weight:700;color:#111827;">${msLast!=null?msLast.toFixed(2)+'%':'—'}</td>
          <td style="padding:6px;text-align:right;font-weight:600;color:${msDelta==null?'#9ca3af':parseFloat(msDelta)>=0?'#16a34a':'#dc2626'}">${msDelta!=null?(parseFloat(msDelta)>=0?'+':'')+msDelta+'%':'—'}</td>
        </tr>
      </tbody>
    </table>`;"""


def find_block_end(text, start_idx):
    """Find the end of the rec-detail innerHTML template:
       starts at backtick after '=', ends at matching closing backtick + ';'.
       Counts nested backticks inside ${...} expressions."""
    # Find opening backtick
    bt = text.index('`', start_idx)
    i = bt + 1
    while i < len(text):
        c = text[i]
        if c == '\\':
            i += 2; continue
        if c == '`':
            # Found closing backtick. Check it's followed by ;
            # (might have nested ${...} though — handled below)
            # Look ahead for ';'
            j = i + 1
            while j < len(text) and text[j] in ' \t':
                j += 1
            if j < len(text) and text[j] == ';':
                return j + 1  # past the ;
            i += 1; continue
        if c == '$' and i+1 < len(text) and text[i+1] == '{':
            # Skip ${...} block — but inside might be more backticks/templates
            depth = 1
            i += 2
            while i < len(text) and depth > 0:
                if text[i] == '\\':
                    i += 2; continue
                if text[i] == '{': depth += 1
                elif text[i] == '}': depth -= 1
                elif text[i] == '`':
                    # Nested template — skip it recursively
                    end = find_block_end(text, i)
                    i = end; continue
                i += 1
            continue
        i += 1
    return -1


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if 'SF_COMPARATIVO_TABLE' in t:
        return 'SKIP already'

    changes = []

    # 1) Remove Médicos button
    btn_pattern = re.compile(r'\s*<button[^>]*data-v="med"[^>]*>Médicos</button>', re.S)
    t, n = btn_pattern.subn('', t, count=1)
    if n: changes.append('btn')

    # 2) Find the detailRows block + innerHTML in renderRec and replace it
    # Search for `const detailRows=[` (only one occurrence in main render).
    dr_match = re.search(r"const detailRows=\[", t)
    if dr_match:
        # Find end: `.filter(Boolean);`
        end_filter = t.find('.filter(Boolean);', dr_match.start())
        if end_filter < 0:
            return f'NO .filter(Boolean) [changes={changes}]'
        end_filter += len('.filter(Boolean);')
        # From here, find the next `document.getElementById('rec-detail').innerHTML=`
        innerHTML_start_marker = "document.getElementById('rec-detail').innerHTML="
        next_render = t.find(innerHTML_start_marker, end_filter)
        if next_render < 0:
            return f'NO innerHTML [changes={changes}]'
        # Find end of innerHTML using template parser
        block_end = find_block_end(t, next_render + len(innerHTML_start_marker))
        if block_end < 0:
            return f'NO template end [changes={changes}]'
        # Replace from dr_match.start() to block_end
        t = t[:dr_match.start()] + NEW_BLOCK + t[block_end:]
        changes.append('table')

    # 3) Remove orphan medDelta declaration
    t, n3 = re.subn(r"\s*const medDelta=[^;]+;\n", "\n", t)
    if n3: changes.append(f'medDelta x{n3}')

    # 4) Safeguard rView='med' -> 'rec'
    rr_match = re.search(r'function renderRec\(\)\{', t)
    if rr_match and "rView==='med'" not in t:
        inj = "if(typeof rView!=='undefined' && rView==='med') rView='rec';\n  "
        t = t[:rr_match.end()] + "\n  " + inj + t[rr_match.end():]
        changes.append('safeguard')

    path.write_text(t, encoding='utf-8', newline='')
    return f'OK [{", ".join(changes)}]'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file(): print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
