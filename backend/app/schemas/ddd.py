from pydantic import BaseModel


class DddMarketOut(BaseModel):
    id: int
    name: str
    clase: str | None
    total_units: int | None
    sie_units: int | None
    global_ms: float | None

    model_config = {"from_attributes": True}


class DddBrandOut(BaseModel):
    id: int
    name: str
    is_siegfried: bool

    model_config = {"from_attributes": True}


class DddBrandMonthlyOut(BaseModel):
    ddd_brand_id: int
    brand_name: str
    region_name: str
    month: int
    units: int | None

    model_config = {"from_attributes": True}


class DddTotalMonthlyOut(BaseModel):
    market_id: int
    region_name: str
    month: int
    units: int | None

    model_config = {"from_attributes": True}


class DddRegionSummaryOut(BaseModel):
    market_id: int
    region_name: str
    total_units: int | None
    sie_units: int | None
    market_share: float | None

    model_config = {"from_attributes": True}


class DddMarketDetailOut(BaseModel):
    market: DddMarketOut
    brands: list[DddBrandOut]
    brand_monthly: list[DddBrandMonthlyOut]
    total_monthly: list[DddTotalMonthlyOut]

    model_config = {"from_attributes": True}
