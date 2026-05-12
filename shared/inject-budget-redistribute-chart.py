"""Agregar al chart de Venta Interna el segmento color ambar 'Redistribuido'
apilado sobre el Budget original, en vez de mostrar solo la barra ajustada."""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# Anchors a buscar y reemplazos.
# 1) Reemplazar el dataset Budget para usar original + agregar dataset Redistribuido
OLD_BUDGET_DS = (
    "{label:'Budget',data:__adjBudget,\n"
    "       backgroundColor:'rgba(107,114,128,.15)',borderColor:'rgba(55,65,81,.5)',\n"
    "       borderWidth:1,borderRadius:3,order:2},"
)
NEW_BUDGET_DS = (
    "{label:'Budget',data:budget,\n"
    "       backgroundColor:'rgba(107,114,128,.15)',borderColor:'rgba(55,65,81,.5)',\n"
    "       borderWidth:1,borderRadius:0,order:3,stack:'budget'},\n"
    "      {label:'Redistribuido',data:__adjBudget.map((v,i)=>Math.max(0,(+v||0)-(+budget[i]||0))),\n"
    "       backgroundColor:'rgba(245,158,11,.55)',borderColor:'rgba(217,119,6,.85)',\n"
    "       borderWidth:1,borderRadius:3,order:2,stack:'budget'},"
)

# 2) Real PM: agregar stack distinto
OLD_REAL_HEAD = "{label:'Real PM',data:real,"
NEW_REAL_HEAD = "{label:'Real PM',stack:'real',data:real,"

# 3) Scales: agregar stacked:true en x e y
#    Anchor de x:  x:{ticks:...}
OLD_SCALE_X = "x:{ticks:{color:'#566c82',font:{size:10,family:'IBM Plex Mono'}},grid:{color:'rgba(255,255,255,.03)'}}"
NEW_SCALE_X = "x:{stacked:true,ticks:{color:'#566c82',font:{size:10,family:'IBM Plex Mono'}},grid:{color:'rgba(255,255,255,.03)'}}"

#    Anchor de y: y:{ticks:...beginAtZero:true}
OLD_SCALE_Y = "y:{ticks:{color:'#566c82',font:{size:10},callback:v=>v>=1000?(v/1000).toFixed(0)+'k':v},\n           grid:{color:'rgba(0,0,0,.18)'},beginAtZero:true}"
NEW_SCALE_Y = "y:{stacked:true,ticks:{color:'#566c82',font:{size:10},callback:v=>v>=1000?(v/1000).toFixed(0)+'k':v},\n           grid:{color:'rgba(0,0,0,.18)'},beginAtZero:true}"


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if "label:'Redistribuido'" in t:
        return 'SKIP already'
    steps = [
        (OLD_BUDGET_DS, NEW_BUDGET_DS, 'Budget DS'),
        (OLD_REAL_HEAD, NEW_REAL_HEAD, 'Real DS head'),
        (OLD_SCALE_X, NEW_SCALE_X, 'scale x'),
        (OLD_SCALE_Y, NEW_SCALE_Y, 'scale y'),
    ]
    missing = []
    for old, new, name in steps:
        if old not in t:
            missing.append(name)
    if missing:
        return f'NO anchors: {missing}'
    for old, new, _ in steps:
        t = t.replace(old, new, 1)
    path.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
