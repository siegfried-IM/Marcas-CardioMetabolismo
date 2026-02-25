from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Brand, Price
from app.schemas.cardio import PriceOut

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
