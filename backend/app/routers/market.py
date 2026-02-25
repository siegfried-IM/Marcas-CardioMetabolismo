from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cardio import (
    Brand,
    MarketAteneo,
    MarketAteneoNational,
    MarketPerformance,
    MarketPerformanceAccumulated,
    MarketPerformanceRegional,
    Molecule,
    Region,
)
from app.schemas.cardio import (
    MarketAteneoNationalOut,
    MarketAteneoOut,
    MarketPerformanceAccumulatedOut,
    MarketPerformanceOut,
    MarketPerformanceRegionalOut,
)

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


@router.get(
    "/market/performance/regional",
    response_model=list[MarketPerformanceRegionalOut],
)
def list_performance_regional(
    molecule: str | None = Query(None),
    region: str | None = Query(None),
    year: int | None = Query(None),
    limit: int = Query(1000, le=10000),
    db: Session = Depends(get_db),
):
    q = (
        db.query(MarketPerformanceRegional)
        .join(Brand, MarketPerformanceRegional.brand_id == Brand.id)
        .join(Molecule, MarketPerformanceRegional.molecule_id == Molecule.id)
        .join(Region, MarketPerformanceRegional.region_id == Region.id)
    )
    if molecule:
        q = q.filter(Molecule.name.ilike(f"%{molecule}%"))
    if region:
        q = q.filter(Region.name.ilike(f"%{region}%"))
    if year:
        q = q.filter(
            func.extract("year", MarketPerformanceRegional.month) == year
        )
    rows = q.order_by(MarketPerformanceRegional.month).limit(limit).all()
    return [
        MarketPerformanceRegionalOut(
            id=r.id,
            brand_id=r.brand_id,
            brand_name=r.brand.name if r.brand else None,
            molecule_name=r.molecule.name if r.molecule else None,
            region_name=r.region.name if r.region else None,
            month=r.month,
            units=r.units,
        )
        for r in rows
    ]


@router.get("/market/ateneo", response_model=list[MarketAteneoOut])
def list_ateneo(
    atc_code: str | None = Query(None),
    region: str | None = Query(None),
    brand_name: str | None = Query(None),
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(MarketAteneo)
    if atc_code:
        q = q.filter(MarketAteneo.atc_code == atc_code)
    if region:
        q = q.filter(MarketAteneo.region.ilike(f"%{region}%"))
    if brand_name:
        q = q.filter(MarketAteneo.brand_name.ilike(f"%{brand_name}%"))
    rows = q.order_by(MarketAteneo.brand_name).limit(limit).all()
    return [
        MarketAteneoOut(
            id=r.id, atc_code=r.atc_code, region=r.region,
            brand_name=r.brand_name, product_name=r.product_name,
            laboratory=r.laboratory, product_code=r.product_code,
            mat_5=r.mat_5, mat_4=r.mat_4, mat_3=r.mat_3,
            mat_2=r.mat_2, mat_current=r.mat_current,
            mes_12=r.mes_12, mes_11=r.mes_11, mes_10=r.mes_10,
            mes_9=r.mes_9, mes_8=r.mes_8, mes_7=r.mes_7,
            mes_6=r.mes_6, mes_5=r.mes_5, mes_4=r.mes_4,
            mes_3=r.mes_3, mes_2=r.mes_2, mes_current=r.mes_current,
            ytd_5=r.ytd_5, ytd_4=r.ytd_4, ytd_3=r.ytd_3,
            ytd_2=r.ytd_2, ytd_current=r.ytd_current,
            ref_date=r.ref_date,
        )
        for r in rows
    ]


@router.get("/market/ateneo/national", response_model=list[MarketAteneoNationalOut])
def list_ateneo_national(
    molecule: str | None = Query(None),
    product: str | None = Query(None),
    period_type: str | None = Query(None),
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(MarketAteneoNational)
    if molecule:
        q = q.filter(MarketAteneoNational.molecule.ilike(f"%{molecule}%"))
    if product:
        q = q.filter(MarketAteneoNational.product_name.ilike(f"%{product}%"))
    if period_type:
        q = q.filter(MarketAteneoNational.period_type == period_type)
    rows = q.order_by(MarketAteneoNational.period_date).limit(limit).all()
    return [
        MarketAteneoNationalOut(
            id=r.id, pack_code=r.pack_code, pack_name=r.pack_name,
            product_name=r.product_name, corporation=r.corporation,
            manufacturer=r.manufacturer, atc_iv=r.atc_iv,
            molecule=r.molecule, pharma_form=r.pharma_form,
            launch_date=r.launch_date, market_type=r.market_type,
            period_type=r.period_type, period_date=r.period_date,
            usd_amount=r.usd_amount, local_amount=r.local_amount,
            units=r.units,
        )
        for r in rows
    ]
