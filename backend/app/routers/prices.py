from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Brand, Price, PriceCatalog
from app.schemas.cardio import PriceCatalogOut, PriceOut

router = APIRouter(tags=["precios"])


@router.get("/prices", response_model=list[PriceOut])
def list_prices(
    brand: str | None = Query(None),
    presentation: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Price).join(Brand)
    if brand:
        q = q.filter(Brand.name == brand)
    if presentation:
        q = q.filter(Price.presentation.ilike(f"%{presentation}%"))
    rows = q.order_by(Brand.name, Price.presentation).all()
    return [
        PriceOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            presentation=r.presentation,
            laboratory=r.laboratory,
            product_name=r.product_name,
            pvp_previous=r.pvp_previous,
            pvp_current=r.pvp_current,
            variation=r.variation,
            is_siegfried=r.is_siegfried,
        )
        for r in rows
    ]


@router.get("/prices/catalog", response_model=list[PriceCatalogOut])
def list_price_catalog(
    drug_name: str | None = Query(None),
    laboratory: str | None = Query(None),
    product_name: str | None = Query(None),
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(PriceCatalog)
    if drug_name:
        q = q.filter(PriceCatalog.drug_name.ilike(f"%{drug_name}%"))
    if laboratory:
        q = q.filter(PriceCatalog.laboratory.ilike(f"%{laboratory}%"))
    if product_name:
        q = q.filter(PriceCatalog.product_name.ilike(f"%{product_name}%"))
    rows = q.order_by(PriceCatalog.product_name).limit(limit).all()
    return [
        PriceCatalogOut(
            id=r.id, registro=r.registro, troquel=r.troquel,
            product_name=r.product_name, presentation=r.presentation,
            drug_name=r.drug_name, pharma_action=r.pharma_action,
            laboratory=r.laboratory, barcode=r.barcode,
            product_type=r.product_type, pami_category=r.pami_category,
            status=r.status, qty_presentations=r.qty_presentations,
            pvp_previous=r.pvp_previous, pvp_current=r.pvp_current,
            variation_pct=r.variation_pct, effective_date=r.effective_date,
            pvp_previous_date=r.pvp_previous_date,
            pvp_current_date=r.pvp_current_date,
        )
        for r in rows
    ]
