from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import (
    Brand,
    Prescription,
    PrescriptionCompetitor,
    PrescriptionMarketShare,
)
from app.schemas.cardio import (
    PrescriptionCompetitorOut,
    PrescriptionMarketShareOut,
    PrescriptionOut,
)

router = APIRouter(tags=["recetas"])


@router.get("/prescriptions", response_model=list[PrescriptionOut])
def list_prescriptions(
    brand_id: int | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Prescription).join(Brand)
    if brand_id:
        q = q.filter(Prescription.brand_id == brand_id)
    if year:
        q = q.filter(func.extract("year", Prescription.month) == year)
    rows = q.order_by(Prescription.month).all()
    return [
        PrescriptionOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            month=r.month,
            prescriptions=r.prescriptions,
            physicians=r.physicians,
        )
        for r in rows
    ]


@router.get(
    "/prescriptions/market-share", response_model=list[PrescriptionMarketShareOut]
)
def list_prescription_ms(
    brand_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(PrescriptionMarketShare).join(Brand)
    if brand_id:
        q = q.filter(PrescriptionMarketShare.brand_id == brand_id)
    rows = q.order_by(PrescriptionMarketShare.month).all()
    return [
        PrescriptionMarketShareOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            month=r.month,
            sie_prescriptions=r.sie_prescriptions,
            market_prescriptions=r.market_prescriptions,
            market_share=r.market_share,
        )
        for r in rows
    ]


@router.get(
    "/prescriptions/competitors", response_model=list[PrescriptionCompetitorOut]
)
def list_prescription_competitors(
    brand: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(PrescriptionCompetitor).join(
        Brand, PrescriptionCompetitor.sie_brand_id == Brand.id
    )
    if brand:
        q = q.filter(Brand.name == brand)
    rows = q.order_by(PrescriptionCompetitor.month).all()
    return [
        PrescriptionCompetitorOut(
            sie_brand_name=r.sie_brand.name,
            competitor_brand_name=r.competitor_brand.name,
            month=r.month,
            prescriptions=r.prescriptions,
        )
        for r in rows
    ]
