from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import (
    Brand,
    MarketPerformance,
    MarketPerformanceAccumulated,
    Molecule,
)
from app.schemas.cardio import MarketPerformanceAccumulatedOut, MarketPerformanceOut

router = APIRouter(tags=["mercado"])


@router.get("/market/performance", response_model=list[MarketPerformanceOut])
def list_performance(
    molecule: str | None = Query(None),
    brand_id: int | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(MarketPerformance).join(Brand).join(Molecule)
    if molecule:
        q = q.filter(Molecule.name == molecule)
    if brand_id:
        q = q.filter(MarketPerformance.brand_id == brand_id)
    if year:
        q = q.filter(
            func.extract("year", MarketPerformance.month) == year
        )
    rows = q.order_by(MarketPerformance.month).all()
    return [
        MarketPerformanceOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            molecule_name=r.molecule.name,
            month=r.month,
            units=r.units,
            market_share=r.market_share,
        )
        for r in rows
    ]


@router.get(
    "/market/performance/accumulated",
    response_model=list[MarketPerformanceAccumulatedOut],
)
def list_performance_accumulated(
    molecule: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(MarketPerformanceAccumulated).join(Brand).join(Molecule)
    if molecule:
        q = q.filter(Molecule.name == molecule)
    if period:
        q = q.filter(MarketPerformanceAccumulated.period_type == period)
    rows = q.order_by(MarketPerformanceAccumulated.ref_date).all()
    return [
        MarketPerformanceAccumulatedOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            molecule_name=r.molecule.name,
            period_type=r.period_type,
            ref_date=r.ref_date,
            units=r.units,
            market_share=r.market_share,
        )
        for r in rows
    ]
