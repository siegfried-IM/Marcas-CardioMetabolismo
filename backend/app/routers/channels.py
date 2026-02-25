from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Brand, ChannelDistribution
from app.schemas.cardio import ChannelDistributionOut

router = APIRouter(tags=["canales"])


@router.get("/channels", response_model=list[ChannelDistributionOut])
def list_channels(db: Session = Depends(get_db)):
    rows = (
        db.query(ChannelDistribution)
        .join(Brand)
        .order_by(Brand.name)
        .all()
    )
    return [
        ChannelDistributionOut(
            brand_id=r.brand_id,
            brand_name=r.brand.name,
            units=r.units,
            conversion_pct=r.conversion_pct,
            counter_pct=r.counter_pct,
        )
        for r in rows
    ]
