from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import Region
from app.models.ddd import (
    DddBrand,
    DddBrandMonthly,
    DddMarket,
    DddRegionSummary,
    DddTotalMonthly,
)
from app.schemas.ddd import (
    DddBrandMonthlyOut,
    DddBrandOut,
    DddMarketDetailOut,
    DddMarketOut,
    DddRegionSummaryOut,
    DddTotalMonthlyOut,
)

router = APIRouter(tags=["ddd"])


@router.get("/ddd/markets", response_model=list[DddMarketOut])
def list_ddd_markets(db: Session = Depends(get_db)):
    return db.query(DddMarket).order_by(DddMarket.name).all()


@router.get("/ddd/markets/{market_id}/brands", response_model=DddMarketDetailOut)
def get_ddd_market_brands(
    market_id: int,
    region_id: list[int] | None = Query(None),
    db: Session = Depends(get_db),
):
    market = db.query(DddMarket).get(market_id)
    brands = (
        db.query(DddBrand)
        .filter(DddBrand.market_id == market_id)
        .order_by(DddBrand.name)
        .all()
    )

    bm_q = (
        db.query(DddBrandMonthly)
        .join(DddBrand)
        .join(Region)
        .filter(DddBrand.market_id == market_id)
    )
    tm_q = (
        db.query(DddTotalMonthly)
        .join(Region)
        .filter(DddTotalMonthly.market_id == market_id)
    )

    if region_id:
        bm_q = bm_q.filter(DddBrandMonthly.region_id.in_(region_id))
        tm_q = tm_q.filter(DddTotalMonthly.region_id.in_(region_id))

    brand_monthly = bm_q.order_by(DddBrandMonthly.month).all()
    total_monthly = tm_q.order_by(DddTotalMonthly.month).all()

    return DddMarketDetailOut(
        market=market,
        brands=[DddBrandOut.model_validate(b) for b in brands],
        brand_monthly=[
            DddBrandMonthlyOut(
                ddd_brand_id=bm.ddd_brand_id,
                brand_name=bm.ddd_brand.name,
                region_name=bm.region.name,
                month=bm.month,
                units=bm.units,
            )
            for bm in brand_monthly
        ],
        total_monthly=[
            DddTotalMonthlyOut(
                market_id=tm.market_id,
                region_name=tm.region.name,
                month=tm.month,
                units=tm.units,
            )
            for tm in total_monthly
        ],
    )


@router.get(
    "/ddd/markets/{market_id}/regions", response_model=list[DddRegionSummaryOut]
)
def list_ddd_regions(
    market_id: int,
    sort_by: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(DddRegionSummary)
        .join(Region)
        .filter(DddRegionSummary.market_id == market_id)
    )
    if sort_by == "market_share":
        q = q.order_by(DddRegionSummary.market_share.desc())
    elif sort_by == "total_units":
        q = q.order_by(DddRegionSummary.total_units.desc())
    else:
        q = q.order_by(Region.name)

    rows = q.all()
    return [
        DddRegionSummaryOut(
            market_id=r.market_id,
            region_name=r.region.name,
            total_units=r.total_units,
            sie_units=r.sie_units,
            market_share=r.market_share,
        )
        for r in rows
    ]
