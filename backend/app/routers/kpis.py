from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Brand, KpiBrand, KpiGlobal
from app.schemas.cardio import KpiBrandOut, KpiGlobalOut

router = APIRouter(tags=["kpis"])


@router.get("/kpis/global", response_model=KpiGlobalOut | None)
def get_kpi_global(db: Session = Depends(get_db)):
    row = db.query(KpiGlobal).order_by(KpiGlobal.loaded_at.desc()).first()
    return row


@router.get("/kpis/brands", response_model=list[KpiBrandOut])
def list_kpi_brands(
    brand_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    sub = db.query(
        KpiBrand.brand_id,
        func.max(KpiBrand.loaded_at).label("max_loaded"),
    ).group_by(KpiBrand.brand_id).subquery()

    q = (
        db.query(KpiBrand)
        .join(Brand)
        .join(
            sub,
            (KpiBrand.brand_id == sub.c.brand_id)
            & (KpiBrand.loaded_at == sub.c.max_loaded),
        )
    )
    if brand_id:
        q = q.filter(KpiBrand.brand_id == brand_id)
    rows = q.order_by(Brand.name).all()
    return [
        KpiBrandOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            loaded_at=r.loaded_at,
            data=r.data,
        )
        for r in rows
    ]
