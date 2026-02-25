# Siegfried BI — Cardio-Metabolismo

Plataforma fullstack de Business Intelligence para la línea Cardio-Metabolismo de Siegfried. Visualiza datos de ventas, mercado IQVIA, recetas, stock, precios y DDD (Dosis Diaria Definida) desde una interfaz React moderna alimentada por una API FastAPI con PostgreSQL.

## Arquitectura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend    │────▶│  Backend    │────▶│ PostgreSQL  │
│  React/Vite  │     │  FastAPI    │     │  16-alpine  │
│  :5173       │     │  :8000      │     │  :5432      │
└─────────────┘     └─────────────┘     └─────────────┘
```

- **Frontend**: React 19 + TypeScript + Vite 6 + Tailwind CSS v4 + Recharts + TanStack Query + Zustand
- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic
- **Base de datos**: PostgreSQL 16 (22 tablas, schema relacional completo)
- **Ingesta**: Script CLI (Typer + openpyxl) que lee archivos Excel y carga con UPSERT

## Inicio rápido

```bash
# 1. Levantar los 3 servicios
docker compose up --build -d

# 2. Cargar datos desde Excel
docker compose exec backend uv run python /app/scripts/ingest.py --all /app/data/

# 3. Abrir en el navegador
open http://localhost:5173
```

| Servicio | URL | Descripción |
|----------|-----|-------------|
| Frontend | http://localhost:5173 | Dashboard React |
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI (auto-generado) |
| DB | localhost:5432 | PostgreSQL (user: `siegfried`, pass: `siegfried_dev`) |

## Estructura del proyecto

```
├── docker-compose.yml          # 3 servicios: db, backend, frontend
├── .env.example                # Variables de entorno
│
├── backend/
│   ├── pyproject.toml          # Dependencias Python (uv)
│   ├── alembic/                # Migraciones de base de datos
│   └── app/
│       ├── main.py             # FastAPI app + CORS + routers
│       ├── models/             # SQLAlchemy models (cardio.py, ddd.py)
│       ├── schemas/            # Pydantic response schemas
│       ├── routers/            # 10 módulos de endpoints
│       └── services/           # Lógica de negocio
│
├── frontend/
│   ├── package.json            # Dependencias Node
│   └── src/
│       ├── pages/              # Hub, CardioBoard, DddBoard
│       ├── components/         # layout/, ui/, charts/
│       ├── api/                # Cliente HTTP + React Query hooks
│       ├── stores/             # Zustand (filtros Cardio/DDD)
│       └── lib/                # Types, constantes, formatters
│
├── scripts/
│   ├── ingest.py               # Ingesta Excel → PostgreSQL
│   └── extract_from_html.py    # Extracción datos HTML → Excel (one-time)
│
└── data/                       # Archivos Excel (.gitignored)
```

## API Endpoints

Prefijo: `/api/v1`

| Dominio | Endpoint | Descripción |
|---------|----------|-------------|
| Catálogo | `GET /brands` | Marcas con molécula y color |
| | `GET /molecules` | Moléculas |
| Budget | `GET /budget?brand_id&year` | Presupuesto vs real mensual |
| Mercado | `GET /market/performance?molecule&year` | Series temporales IQVIA |
| | `GET /market/performance/accumulated` | Acumulados YTD/MAT |
| Recetas | `GET /prescriptions?brand_id&year` | Recetas + médicos |
| | `GET /prescriptions/market-share` | MS% recetas |
| | `GET /prescriptions/competitors?brand` | Competidores |
| Canales | `GET /channels` | Distribución convenios/mostrador |
| Convenios | `GET /agreements?brand_id` | Por obra social |
| Precios | `GET /prices?brand` | SIE vs competidores |
| Stock | `GET /stock/brands?brand_id&year` | Stock a nivel marca |
| | `GET /stock/presentations?brand_id&status` | Por presentación |
| KPIs | `GET /kpis/global` | KPI strip global (JSONB) |
| | `GET /kpis/brands?brand_id` | KPIs por marca (JSONB) |
| DDD | `GET /ddd/markets` | Mercados DDD |
| | `GET /ddd/markets/{id}/brands?region_id` | Marcas + series mensuales |
| | `GET /ddd/markets/{id}/regions?sort_by` | Tabla regional |

## Ingesta de datos

El script detecta el tipo de archivo por las hojas que contiene:

```bash
# Un archivo específico
docker compose exec backend uv run python /app/scripts/ingest.py /app/data/cardio_ventas.xlsx

# Todos los Excel del directorio
docker compose exec backend uv run python /app/scripts/ingest.py --all /app/data/

# Solo validar sin escribir
docker compose exec backend uv run python /app/scripts/ingest.py --dry-run /app/data/ddd_data.xlsx
```

### Formato de los Excel

| Archivo | Hojas |
|---------|-------|
| `cardio_ventas.xlsx` | Budget, Canales, KPIs |
| `cardio_mercado.xlsx` | Productos, Performance |
| `cardio_recetas_stock.xlsx` | Recetas, Recetas_MS, Convenios, Stock_Marca, Stock_Presentación, Precios |
| `ddd_data.xlsx` | Mercados, Marcas, Datos_Mensuales |

## Dashboards

### Hub (`/`)
Página de navegación con acceso a las líneas terapéuticas.

### Cardio-Metabolismo (`/cardio`)
Dashboard principal con 9 secciones:
1. **Presupuesto** — Gráfico de barras budget vs real
2. **Performance de Mercado** — Líneas multi-serie por molécula
3. **Recetas Médicas** — Evolución mensual de prescripciones
4. **Market Share de Recetas** — Barras por marca
5. **Competidores** — Ranking por recetas
6. **Canales** — Distribución convenios/mostrador (donut)
7. **Convenios** — Tabla sorteable por obra social
8. **Stock y Cobertura** — Gráfico mixto barras+línea + tabla de presentaciones
9. **Precios** — Comparativo SIE vs competidores

### DDD (`/cardio/ddd`)
Dashboard de Dosis Diaria Definida:
- Selector de mercado + KPIs
- Dropdown multi-select de regiones
- Gráficos de línea mensuales por marca
- Tabla regional con resumen

## Desarrollo local

```bash
# Backend (sin Docker)
cd backend
uv sync
DATABASE_URL=postgresql://siegfried:siegfried_dev@localhost:5432/siegfried_bi uv run uvicorn app.main:app --reload

# Frontend (sin Docker)
cd frontend
npm install
npm run dev

# Migraciones
cd backend
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "descripcion"
```

## Stack técnico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Frontend | React | 19 |
| Bundler | Vite | 6 |
| CSS | Tailwind CSS | 4 |
| Charts | Recharts | 2.15 |
| State | Zustand | 5 |
| Data fetching | TanStack Query | 5 |
| Routing | React Router | 7 |
| Backend | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.14+ |
| Database | PostgreSQL | 16 |
| Package mgr (Python) | uv | latest |
| Container | Docker Compose | v2 |
