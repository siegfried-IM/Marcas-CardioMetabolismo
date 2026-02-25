from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Agreement, Brand
from app.schemas.cardio import AgreementOut

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
