"""Script CLI de ingesta: Excel → PostgreSQL.

Detecta el tipo de archivo por las hojas que contiene y carga los datos
usando UPSERT (ON CONFLICT DO UPDATE).

Uso:
    uv run python scripts/ingest.py data/cardio_ventas.xlsx
    uv run python scripts/ingest.py --all data/
    uv run python scripts/ingest.py --dry-run data/ddd_data.xlsx
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import typer
from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.database import Base
from app.models.cardio import (
    Agreement,
    Brand,
    BudgetEntry,
    ChannelDistribution,
    KpiBrand,
    KpiGlobal,
    MarketPerformance,
    Molecule,
    Presentation,
    Prescription,
    PrescriptionCompetitor,
    PrescriptionMarketShare,
    Price,
    Region,
    StockBrand,
    StockPresentation,
)
from app.models.ddd import (
    DddBrand,
    DddBrandMonthly,
    DddMarket,
    DddRegionSummary,
    DddTotalMonthly,
)

app = typer.Typer(help="Siegfried BI — Ingesta de datos Excel")

MONTH_NAMES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def get_session() -> Session:
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://siegfried:siegfried_dev@localhost:5432/siegfried_bi"
    )
    engine = create_engine(db_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def get_or_create_brand(db: Session, name: str, **kwargs) -> Brand:
    brand = db.query(Brand).filter(Brand.name == name).first()
    if not brand:
        brand = Brand(name=name, **kwargs)
        db.add(brand)
        db.flush()
    return brand


def get_or_create_molecule(db: Session, name: str, clase: str | None = None) -> Molecule:
    mol = db.query(Molecule).filter(Molecule.name == name).first()
    if not mol:
        mol = Molecule(name=name, clase=clase)
        db.add(mol)
        db.flush()
    return mol


def get_or_create_region(db: Session, name: str) -> Region:
    reg = db.query(Region).filter(Region.name == name).first()
    if not reg:
        reg = Region(name=name)
        db.add(reg)
        db.flush()
    return reg


def get_or_create_presentation(
    db: Session, brand_id: int, name: str, familia: str | None = None
) -> Presentation:
    pres = (
        db.query(Presentation)
        .filter(Presentation.brand_id == brand_id, Presentation.name == name)
        .first()
    )
    if not pres:
        pres = Presentation(brand_id=brand_id, name=name, familia=familia)
        db.add(pres)
        db.flush()
    return pres


def detect_file_type(wb) -> str:
    sheets = set(wb.sheetnames)
    if "Budget" in sheets or "Canales" in sheets or "KPIs" in sheets:
        return "cardio_ventas"
    if "Productos" in sheets or "Performance" in sheets:
        return "cardio_mercado"
    if "Recetas" in sheets or "Stock_Marca" in sheets:
        return "cardio_recetas_stock"
    if "Mercados" in sheets or "Datos_Mensuales" in sheets:
        return "ddd_data"
    raise ValueError(f"No se pudo detectar el tipo de archivo. Hojas: {sheets}")


def read_sheet_rows(ws):
    """Lee una hoja como lista de dicts usando la primera fila como headers."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
    return [dict(zip(headers, row)) for row in rows[1:] if any(v is not None for v in row)]


def ingest_cardio_ventas(db: Session, wb, dry_run: bool = False) -> dict:
    stats = {"budget": 0, "canales": 0, "kpis_global": 0, "kpis_brand": 0}
    errors = []

    # Budget
    if "Budget" in wb.sheetnames:
        for row in read_sheet_rows(wb["Budget"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                year = int(row["Año"])
                for m in range(1, 13):
                    b_key = f"{MONTH_NAMES[m-1]}_Budget"
                    a_key = f"{MONTH_NAMES[m-1]}_Real"
                    budget_val = row.get(b_key)
                    actual_val = row.get(a_key)
                    if budget_val is None and actual_val is None:
                        continue
                    existing = (
                        db.query(BudgetEntry)
                        .filter_by(brand_id=brand.id, year=year, month=m)
                        .first()
                    )
                    if existing:
                        existing.budget = int(budget_val) if budget_val else None
                        existing.actual = int(actual_val) if actual_val else None
                    else:
                        db.add(BudgetEntry(
                            brand_id=brand.id, year=year, month=m,
                            budget=int(budget_val) if budget_val else None,
                            actual=int(actual_val) if actual_val else None,
                        ))
                    stats["budget"] += 1
            except Exception as e:
                errors.append(f"Budget: {row.get('Marca', '?')} - {e}")

    # Canales
    if "Canales" in wb.sheetnames:
        for row in read_sheet_rows(wb["Canales"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                existing = db.query(ChannelDistribution).filter_by(brand_id=brand.id).first()
                if existing:
                    existing.units = int(row["Unidades"])
                    existing.conversion_pct = float(row["Convenios_%"]) if row.get("Convenios_%") else None
                    existing.counter_pct = float(row["Mostrador_%"]) if row.get("Mostrador_%") else None
                else:
                    db.add(ChannelDistribution(
                        brand_id=brand.id, units=int(row["Unidades"]),
                        conversion_pct=float(row["Convenios_%"]) if row.get("Convenios_%") else None,
                        counter_pct=float(row["Mostrador_%"]) if row.get("Mostrador_%") else None,
                    ))
                stats["canales"] += 1
            except Exception as e:
                errors.append(f"Canales: {row.get('Marca', '?')} - {e}")

    # KPIs
    if "KPIs" in wb.sheetnames:
        for row in read_sheet_rows(wb["KPIs"]):
            try:
                if "KPI_Global" in str(row.get("Tipo", "")):
                    data = {k: v for k, v in row.items() if k != "Tipo" and v is not None}
                    db.add(KpiGlobal(data=data))
                    stats["kpis_global"] += 1
                else:
                    brand_name = row.get("Marca")
                    if brand_name:
                        brand = get_or_create_brand(db, brand_name, is_siegfried=True)
                        data = {k: v for k, v in row.items() if k not in ("Tipo", "Marca") and v is not None}
                        db.add(KpiBrand(brand_id=brand.id, data=data))
                        stats["kpis_brand"] += 1
            except Exception as e:
                errors.append(f"KPIs: {e}")

    if not dry_run:
        db.commit()
    return {"stats": stats, "errors": errors}


def ingest_cardio_mercado(db: Session, wb, dry_run: bool = False) -> dict:
    stats = {"products": 0, "performance": 0}
    errors = []

    # Productos (catálogo)
    if "Productos" in wb.sheetnames:
        for row in read_sheet_rows(wb["Productos"]):
            try:
                mol = get_or_create_molecule(db, row["Molécula"])
                brand = get_or_create_brand(
                    db, row["Producto"],
                    molecule_id=mol.id,
                    manufacturer=row.get("Laboratorio"),
                    is_siegfried=bool(row.get("Es_Siegfried")),
                )
                stats["products"] += 1
            except Exception as e:
                errors.append(f"Productos: {row.get('Producto', '?')} - {e}")

    # Performance (formato largo)
    if "Performance" in wb.sheetnames:
        for row in read_sheet_rows(wb["Performance"]):
            try:
                mol = get_or_create_molecule(db, row["Molécula"])
                brand = get_or_create_brand(db, row["Producto"], molecule_id=mol.id)
                month_val = row["Mes"]
                if isinstance(month_val, str):
                    parts = month_val.split("-")
                    month_date = date(int(parts[0]), int(parts[1]), 1)
                else:
                    month_date = date(month_val.year, month_val.month, 1)

                existing = (
                    db.query(MarketPerformance)
                    .filter_by(brand_id=brand.id, molecule_id=mol.id, month=month_date)
                    .first()
                )
                if existing:
                    existing.units = int(row["Unidades"]) if row.get("Unidades") else None
                    existing.market_share = float(row["MS_%"]) if row.get("MS_%") else None
                else:
                    db.add(MarketPerformance(
                        brand_id=brand.id, molecule_id=mol.id, month=month_date,
                        units=int(row["Unidades"]) if row.get("Unidades") else None,
                        market_share=float(row["MS_%"]) if row.get("MS_%") else None,
                    ))
                stats["performance"] += 1
            except Exception as e:
                errors.append(f"Performance: {row.get('Producto', '?')} - {e}")

    if not dry_run:
        db.commit()
    return {"stats": stats, "errors": errors}


def ingest_cardio_recetas_stock(db: Session, wb, dry_run: bool = False) -> dict:
    stats = {"recetas": 0, "recetas_ms": 0, "convenios": 0, "stock_marca": 0, "stock_pres": 0, "precios": 0}
    errors = []

    def parse_month(val) -> date:
        if isinstance(val, str):
            parts = val.split("-")
            return date(int(parts[0]), int(parts[1]), 1)
        return date(val.year, val.month, 1)

    # Recetas
    if "Recetas" in wb.sheetnames:
        for row in read_sheet_rows(wb["Recetas"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                month_date = parse_month(row["Mes"])
                rx_val = row.get("Recetas")
                md_val = row.get("Médicos")
                if rx_val is None or md_val is None:
                    continue
                existing = db.query(Prescription).filter_by(brand_id=brand.id, month=month_date).first()
                if existing:
                    existing.prescriptions = int(rx_val)
                    existing.physicians = int(md_val)
                else:
                    db.add(Prescription(
                        brand_id=brand.id, month=month_date,
                        prescriptions=int(rx_val), physicians=int(md_val),
                    ))
                stats["recetas"] += 1
            except Exception as e:
                errors.append(f"Recetas: {row.get('Marca', '?')} - {e}")

    # Recetas_MS
    if "Recetas_MS" in wb.sheetnames:
        for row in read_sheet_rows(wb["Recetas_MS"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                month_date = parse_month(row["Mes"])
                existing = db.query(PrescriptionMarketShare).filter_by(brand_id=brand.id, month=month_date).first()
                if existing:
                    existing.sie_prescriptions = int(row["Recetas_SIE"]) if row.get("Recetas_SIE") else None
                    existing.market_prescriptions = int(row["Recetas_Mercado"]) if row.get("Recetas_Mercado") else None
                    existing.market_share = float(row["MS_%"]) if row.get("MS_%") else None
                else:
                    db.add(PrescriptionMarketShare(
                        brand_id=brand.id, month=month_date,
                        sie_prescriptions=int(row["Recetas_SIE"]) if row.get("Recetas_SIE") else None,
                        market_prescriptions=int(row["Recetas_Mercado"]) if row.get("Recetas_Mercado") else None,
                        market_share=float(row["MS_%"]) if row.get("MS_%") else None,
                    ))
                stats["recetas_ms"] += 1
            except Exception as e:
                errors.append(f"Recetas_MS: {row.get('Marca', '?')} - {e}")

    # Convenios
    if "Convenios" in wb.sheetnames:
        for row in read_sheet_rows(wb["Convenios"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                existing = db.query(Agreement).filter_by(brand_id=brand.id, health_plan=row["Obra_Social"]).first()
                if existing:
                    existing.units_current = int(row["Unid_2025"]) if row.get("Unid_2025") else None
                    existing.units_previous = int(row["Unid_2024"]) if row.get("Unid_2024") else None
                    existing.delta_pct = int(row["Delta_%"]) if row.get("Delta_%") else None
                    existing.net_amount = float(row["Neto_$"]) if row.get("Neto_$") else None
                else:
                    db.add(Agreement(
                        brand_id=brand.id, health_plan=row["Obra_Social"],
                        units_current=int(row["Unid_2025"]) if row.get("Unid_2025") else None,
                        units_previous=int(row["Unid_2024"]) if row.get("Unid_2024") else None,
                        delta_pct=int(row["Delta_%"]) if row.get("Delta_%") else None,
                        net_amount=float(row["Neto_$"]) if row.get("Neto_$") else None,
                    ))
                stats["convenios"] += 1
            except Exception as e:
                errors.append(f"Convenios: {row.get('Marca', '?')} - {e}")

    # Stock_Marca
    if "Stock_Marca" in wb.sheetnames:
        for row in read_sheet_rows(wb["Stock_Marca"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                month_date = parse_month(row["Mes"])
                existing = db.query(StockBrand).filter_by(brand_id=brand.id, month=month_date).first()
                if existing:
                    existing.days_cover = int(row["Dias"]) if row.get("Dias") else None
                    existing.sales = int(row["Ventas"]) if row.get("Ventas") else None
                    existing.stock_units = int(row.get("Stock", 0)) if row.get("Stock") else None
                else:
                    db.add(StockBrand(
                        brand_id=brand.id, month=month_date,
                        days_cover=int(row["Dias"]) if row.get("Dias") else None,
                        sales=int(row["Ventas"]) if row.get("Ventas") else None,
                        stock_units=int(row.get("Stock", 0)) if row.get("Stock") else None,
                    ))
                stats["stock_marca"] += 1
            except Exception as e:
                errors.append(f"Stock_Marca: {row.get('Marca', '?')} - {e}")

    # Stock_Presentación
    if "Stock_Presentación" in wb.sheetnames:
        for row in read_sheet_rows(wb["Stock_Presentación"]):
            try:
                brand = get_or_create_brand(db, row["Marca"], is_siegfried=True)
                pres = get_or_create_presentation(
                    db, brand.id, row["Presentación"], familia=row.get("Familia")
                )
                month_date = parse_month(row["Mes"])
                existing = db.query(StockPresentation).filter_by(presentation_id=pres.id, month=month_date).first()
                if existing:
                    existing.sales = int(row["Ventas"]) if row.get("Ventas") else None
                    existing.days_cover = int(row["Dias"]) if row.get("Dias") else None
                    existing.status = row.get("Estado")
                else:
                    db.add(StockPresentation(
                        presentation_id=pres.id, month=month_date,
                        sales=int(row["Ventas"]) if row.get("Ventas") else None,
                        days_cover=int(row["Dias"]) if row.get("Dias") else None,
                        status=row.get("Estado"),
                    ))
                stats["stock_pres"] += 1
            except Exception as e:
                errors.append(f"Stock_Pres: {row.get('Presentación', '?')} - {e}")

    # Precios
    if "Precios" in wb.sheetnames:
        for row in read_sheet_rows(wb["Precios"]):
            try:
                brand = get_or_create_brand(db, row["Marca_Ref"], is_siegfried=True)
                existing = (
                    db.query(Price)
                    .filter_by(brand_id=brand.id, presentation=row["Presentación"], product_name=row["Producto"])
                    .first()
                )
                if existing:
                    existing.laboratory = row["Laboratorio"]
                    existing.pvp_previous = float(row["PVP_Ant"]) if row.get("PVP_Ant") else None
                    existing.pvp_current = float(row["PVP_Act"]) if row.get("PVP_Act") else None
                    existing.variation = float(row["Var_%"]) if row.get("Var_%") else None
                    existing.is_siegfried = bool(row.get("Es_SIE"))
                else:
                    db.add(Price(
                        brand_id=brand.id, presentation=row["Presentación"],
                        laboratory=row["Laboratorio"], product_name=row["Producto"],
                        pvp_previous=float(row["PVP_Ant"]) if row.get("PVP_Ant") else None,
                        pvp_current=float(row["PVP_Act"]) if row.get("PVP_Act") else None,
                        variation=float(row["Var_%"]) if row.get("Var_%") else None,
                        is_siegfried=bool(row.get("Es_SIE")),
                    ))
                stats["precios"] += 1
            except Exception as e:
                errors.append(f"Precios: {row.get('Producto', '?')} - {e}")

    if not dry_run:
        db.commit()
    return {"stats": stats, "errors": errors}


def ingest_ddd_data(db: Session, wb, dry_run: bool = False) -> dict:
    stats = {"mercados": 0, "marcas": 0, "datos_mensuales": 0}
    errors = []

    market_cache: dict[str, DddMarket] = {}

    # Mercados
    if "Mercados" in wb.sheetnames:
        for row in read_sheet_rows(wb["Mercados"]):
            try:
                name = row["Mercado"]
                existing = db.query(DddMarket).filter_by(name=name).first()
                if existing:
                    existing.clase = row.get("Clase")
                    existing.total_units = int(row["Total_Unid"]) if row.get("Total_Unid") else None
                    existing.sie_units = int(row["Unid_SIE"]) if row.get("Unid_SIE") else None
                    existing.global_ms = float(row["MS_%"]) if row.get("MS_%") else None
                    market_cache[name] = existing
                else:
                    m = DddMarket(
                        name=name, clase=row.get("Clase"),
                        total_units=int(row["Total_Unid"]) if row.get("Total_Unid") else None,
                        sie_units=int(row["Unid_SIE"]) if row.get("Unid_SIE") else None,
                        global_ms=float(row["MS_%"]) if row.get("MS_%") else None,
                    )
                    db.add(m)
                    db.flush()
                    market_cache[name] = m
                stats["mercados"] += 1
            except Exception as e:
                errors.append(f"Mercados: {row.get('Mercado', '?')} - {e}")

    # Marcas
    brand_cache: dict[tuple[str, str], DddBrand] = {}
    if "Marcas" in wb.sheetnames:
        for row in read_sheet_rows(wb["Marcas"]):
            try:
                mkt_name = row["Mercado"]
                if mkt_name not in market_cache:
                    market_cache[mkt_name] = db.query(DddMarket).filter_by(name=mkt_name).one()
                market = market_cache[mkt_name]
                brand_name = row["Marca"]
                existing = db.query(DddBrand).filter_by(market_id=market.id, name=brand_name).first()
                if existing:
                    existing.is_siegfried = bool(row.get("Es_SIE"))
                    brand_cache[(mkt_name, brand_name)] = existing
                else:
                    b = DddBrand(
                        market_id=market.id, name=brand_name,
                        is_siegfried=bool(row.get("Es_SIE")),
                    )
                    db.add(b)
                    db.flush()
                    brand_cache[(mkt_name, brand_name)] = b
                stats["marcas"] += 1
            except Exception as e:
                errors.append(f"Marcas DDD: {row.get('Marca', '?')} - {e}")

    # Datos_Mensuales (formato ancho)
    if "Datos_Mensuales" in wb.sheetnames:
        for row in read_sheet_rows(wb["Datos_Mensuales"]):
            try:
                mkt_name = row["Mercado"]
                brand_name = row.get("Marca")
                region_name = row["Región"]
                region = get_or_create_region(db, region_name)

                if mkt_name not in market_cache:
                    market_cache[mkt_name] = db.query(DddMarket).filter_by(name=mkt_name).one()
                market = market_cache[mkt_name]

                for m in range(1, 13):
                    val = row.get(MONTH_NAMES[m - 1])
                    if val is None:
                        continue

                    if brand_name and brand_name != "__TOTAL__":
                        key = (mkt_name, brand_name)
                        if key not in brand_cache:
                            existing_b = db.query(DddBrand).filter_by(
                                market_id=market.id, name=brand_name
                            ).first()
                            if not existing_b:
                                existing_b = DddBrand(market_id=market.id, name=brand_name, is_siegfried=False)
                                db.add(existing_b)
                                db.flush()
                            brand_cache[key] = existing_b
                        ddd_brand = brand_cache[key]
                        existing = db.query(DddBrandMonthly).filter_by(
                            ddd_brand_id=ddd_brand.id, region_id=region.id, month=m
                        ).first()
                        if existing:
                            existing.units = int(val)
                        else:
                            db.add(DddBrandMonthly(
                                ddd_brand_id=ddd_brand.id, region_id=region.id,
                                month=m, units=int(val),
                            ))
                    else:
                        existing = db.query(DddTotalMonthly).filter_by(
                            market_id=market.id, region_id=region.id, month=m
                        ).first()
                        if existing:
                            existing.units = int(val)
                        else:
                            db.add(DddTotalMonthly(
                                market_id=market.id, region_id=region.id,
                                month=m, units=int(val),
                            ))
                    stats["datos_mensuales"] += 1
            except Exception as e:
                errors.append(f"Datos_Mensuales: {row.get('Marca', '?')} - {e}")

    if not dry_run:
        db.commit()
    return {"stats": stats, "errors": errors}


INGESTORS = {
    "cardio_ventas": ingest_cardio_ventas,
    "cardio_mercado": ingest_cardio_mercado,
    "cardio_recetas_stock": ingest_cardio_recetas_stock,
    "ddd_data": ingest_ddd_data,
}


def process_file(path: Path, dry_run: bool = False, strict: bool = False) -> None:
    typer.echo(f"\n{'='*60}")
    typer.echo(f"Procesando: {path.name}")

    wb = load_workbook(path, read_only=True, data_only=True)
    file_type = detect_file_type(wb)
    typer.echo(f"Tipo detectado: {file_type}")

    db = get_session()
    try:
        result = INGESTORS[file_type](db, wb, dry_run=dry_run)

        typer.echo(f"\nResultados {'(DRY RUN)' if dry_run else ''}:")
        for key, val in result["stats"].items():
            typer.echo(f"  {key}: {val} filas")

        if result["errors"]:
            typer.echo(f"\nErrores ({len(result['errors'])}):")
            for err in result["errors"][:20]:
                typer.echo(f"  ! {err}")
            if strict:
                db.rollback()
                typer.echo("STRICT MODE: rollback realizado")
                raise typer.Exit(1)
    finally:
        db.close()
        wb.close()


@app.command()
def main(
    path: str = typer.Argument(help="Ruta al archivo Excel o directorio"),
    all: bool = typer.Option(False, "--all", help="Procesar todos los xlsx del directorio"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo validar, no escribir"),
    strict: bool = typer.Option(False, "--strict", help="Abortar en cualquier error"),
):
    """Ingesta de datos Excel a PostgreSQL."""
    p = Path(path)

    if all and p.is_dir():
        files = sorted(p.glob("*.xlsx"))
        if not files:
            typer.echo(f"No se encontraron archivos .xlsx en {p}")
            raise typer.Exit(1)
        for f in files:
            process_file(f, dry_run=dry_run, strict=strict)
    elif p.is_file():
        process_file(p, dry_run=dry_run, strict=strict)
    else:
        typer.echo(f"Ruta inválida: {path}")
        raise typer.Exit(1)

    typer.echo("\nIngesta completada.")


if __name__ == "__main__":
    app()
