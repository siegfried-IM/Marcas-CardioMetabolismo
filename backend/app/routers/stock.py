from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Brand, Presentation, StockBrand, StockPresentation
from app.schemas.cardio import StockBrandOut, StockPresentationOut

router = APIRouter(tags=["stock"])


@router.get("/stock/brands", response_model=list[StockBrandOut])
def list_stock_brands(
    brand_id: int | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StockBrand).join(Brand)
    if brand_id:
        q = q.filter(StockBrand.brand_id == brand_id)
    if year:
        q = q.filter(func.extract("year", StockBrand.month) == year)
    rows = q.order_by(StockBrand.month).all()
    return [
        StockBrandOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            month=r.month,
            days_cover=r.days_cover,
            sales=r.sales,
            stock_units=r.stock_units,
        )
        for r in rows
    ]


@router.get("/stock/presentations", response_model=list[StockPresentationOut])
def list_stock_presentations(
    brand_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StockPresentation).join(Presentation).join(Brand)
    if brand_id:
        q = q.filter(Presentation.brand_id == brand_id)
    if status:
        q = q.filter(StockPresentation.status == status)
    rows = q.order_by(Presentation.name, StockPresentation.month).all()
    return [
        StockPresentationOut(
            presentation_id=r.presentation_id,
            presentation_name=r.presentation.name,
            brand_name=r.presentation.brand.name,
            familia=r.presentation.familia,
            month=r.month,
            sales=r.sales,
            days_cover=r.days_cover,
            status=r.status,
        )
        for r in rows
    ]
