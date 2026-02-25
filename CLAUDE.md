# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Dashboards estáticos de marketing para **Siegfried BI** — línea Cardio-Metabolismo. Sitio desplegado en GitHub Pages bajo la organización `SIEGFRIED-BI`.

## Arquitectura

Archivos HTML standalone con CSS y JS inline (sin build system, sin bundler, sin dependencias npm):

- `index.html` — Hub principal de marketing. Lista las líneas terapéuticas (Cardio, Antibióticos, Respiratoria, etc.) con links configurables vía `localStorage` (`sie_hub_urls`). Tipografía: IBM Plex Sans/Mono.
- `cardio/index.html` — Dashboard de gestión de marcas de la línea Cardio-Metabolismo. Usa Chart.js 4.4.1 (CDN) para gráficos. Tipografía: IBM Plex Sans/Mono. ~1800 líneas.
- `cardio/DDD/index.html` — Dashboard de DDD (Dosis Diaria Definida). Usa Chart.js 4.4.1 (CDN). Tipografía: Inter. ~440 líneas.

## Convenciones

- **Idioma**: Todo el contenido visible (UI, labels, textos) en español
- **Estilos**: CSS inline en `<style>` dentro de cada HTML. Variables CSS en `:root` con paleta corporativa (rojo Siegfried `#B01E1E` / `#7A1518`)
- **JS**: Scripts inline al final del `<body>`. Datos hardcoded en el HTML (no hay API ni fetch externo de datos)
- **Dependencia externa única**: Chart.js 4.4.1 vía CDN (`cdnjs.cloudflare.com`)
- **Sin sistema de build**: Para desarrollo, abrir los HTML directamente en el navegador o usar un servidor local (`python -m http.server`)

## Desarrollo

```bash
# Servidor local desde la raíz del repo
cd Marcas-CardioMetabolismo
python3 -m http.server 8000
# Abrir http://localhost:8000
```

No hay tests, linter, ni pipeline de CI. Los cambios se verifican visualmente en el navegador.
