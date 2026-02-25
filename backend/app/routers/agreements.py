from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Agreement, AgreementDetail, Brand
from app.schemas.cardio import AgreementDetailOut, AgreementOut

router = APIRouter(tags=["convenios"])


@router.get("/agreements", response_model=list[AgreementOut])
def list_agreements(
    brand_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Agreement).join(Brand)
    if brand_id:
        q = q.filter(Agreement.brand_id == brand_id)
    rows = q.order_by(Brand.name, Agreement.health_plan).all()
    return [
        AgreementOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            health_plan=r.health_plan,
            units_current=r.units_current,
            units_previous=r.units_previous,
            delta_pct=r.delta_pct,
            net_amount=r.net_amount,
        )
        for r in rows
    ]


@router.get("/agreements/details", response_model=list[AgreementDetailOut])
def list_agreement_details(
    brand_id: int | None = Query(None),
    health_plan: str | None = Query(None),
    familia: str | None = Query(None),
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(AgreementDetail)
    if brand_id:
        q = q.filter(AgreementDetail.brand_id == brand_id)
    if health_plan:
        q = q.filter(AgreementDetail.health_plan.ilike(f"%{health_plan}%"))
    if familia:
        q = q.filter(AgreementDetail.familia.ilike(f"%{familia}%"))
    rows = q.order_by(AgreementDetail.health_plan).limit(limit).all()
    return [
        AgreementDetailOut(
            id=r.id,
            brand_id=r.brand_id,
            brand_name=r.brand.name if r.brand else None,
            laboratory=r.laboratory,
            line=r.line,
            familia=r.familia,
            health_plan=r.health_plan,
            health_plan_detail=r.health_plan_detail,
            product_name=r.product_name,
            units=r.units,
            pvp_amount=r.pvp_amount,
            system_coverage=r.system_coverage,
            lab_pvp_contribution=r.lab_pvp_contribution,
            lab_adjustment=r.lab_adjustment,
            lab_total_contribution=r.lab_total_contribution,
            net_contribution=r.net_contribution,
            report_date=r.report_date,
        )
        for r in rows
    ]
