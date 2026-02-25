from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Brand, BudgetEntry
from app.schemas.cardio import BudgetEntryOut

router = APIRouter(tags=["budget"])


@router.get("/budget", response_model=list[BudgetEntryOut])
def list_budget(
    brand_id: int | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(BudgetEntry).join(Brand)
    if brand_id:
        q = q.filter(BudgetEntry.brand_id == brand_id)
    if year:
        q = q.filter(BudgetEntry.year == year)
    rows = q.order_by(BudgetEntry.year, BudgetEntry.month).all()
    return [
        BudgetEntryOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            year=r.year,
            month=r.month,
            budget=r.budget,
            actual=r.actual,
        )
        for r in rows
    ]
