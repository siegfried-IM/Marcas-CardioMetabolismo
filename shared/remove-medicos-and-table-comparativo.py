"""Saca Medicos de Recetas (boton + datos) y convierte el Comparativo
en tabla en las 7 lineas. Idempotente."""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# Nuevo render del Comparativo como tabla
NEW_COMPARATIVO_RENDER = '''document.getElementById('rec-detail').innerHTML=`
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
    </table>`;'''


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if "// Medicos removed" in t and "<table style" in t:
        return 'SKIP already'

    changes = 0

    # 1) Remove "Médicos" button from rec-view-ctrl
    btn_pattern = re.compile(r'\s*<button[^>]*data-v="med"[^>]*>Médicos</button>', re.S)
    t, n = btn_pattern.subn('', t, count=1)
    if n: changes += 1

    # 2) Replace the rec-detail innerHTML rendering with table version
    # Look for the document.getElementById('rec-detail').innerHTML=` ... `;
    # Use the marker 'Comparativo</p>' to find the start
    start_marker = "document.getElementById('rec-detail').innerHTML=`"
    if start_marker in t:
        start = t.index(start_marker)
        # Find the closing backtick + ;  after start
        i = start + len(start_marker)
        depth = 0
        while i < len(t):
            c = t[i]
            if c == '`' and t[i-1] != '\\':
                break
            i += 1
        if i < len(t):
            # Now find ;
            end = t.index(';', i) + 1
            t = t[:start] + NEW_COMPARATIVO_RENDER + t[end:]
            changes += 1

    # 3) Remove medDelta and Medicos rows from detailRows building (cleanup)
    t = re.sub(r"\s*const medDelta=[^;]+;\n", "\n  // Medicos removed (data inconsistente desde CloseUp)\n", t, count=1)

    # 4) Make sure 'med' option in rView is reset to 'rec' if active
    # In case state is in 'med', renderRec should fallback. We add a defensive check.
    t = re.sub(r"(let rView='rec')", r"\1 /* med option removed */", t, count=1)
    # If rView was 'med' from somewhere, normalize to 'rec'
    # Add safeguard at renderRec start
    rr_match = re.search(r'function renderRec\(\)\{', t)
    if rr_match and "if(rView==='med')" not in t:
        inj = "if(rView==='med') rView='rec';\n  "
        t = t[:rr_match.end()] + "\n  " + inj + t[rr_match.end():]

    path.write_text(t, encoding='utf-8', newline='')
    return f'OK ({changes} changes)'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file(): print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
