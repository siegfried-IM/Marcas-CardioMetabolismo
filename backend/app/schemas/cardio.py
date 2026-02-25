from datetime import date, datetime

from pydantic import BaseModel


# --- Catálogos ---


class MoleculeOut(BaseModel):
    id: int
    name: str
    clase: str | None

    model_config = {"from_attributes": True}


class BrandOut(BaseModel):
    id: int
    name: str
    molecule_id: int | None
    molecule_name: str | None = None
    manufacturer: str | None
    is_siegfried: bool
    color: str | None

    model_config = {"from_attributes": True}


# --- Budget ---


class BudgetEntryOut(BaseModel):
    brand_id: int
    brand_name: str
    year: int
    month: int
    budget: int | None
    actual: int | None

    model_config = {"from_attributes": True}


# --- Market Performance ---


class MarketPerformanceOut(BaseModel):
    brand_id: int
    brand_name: str
    molecule_name: str
    month: date
    units: int | None
    market_share: float | None

    model_config = {"from_attributes": True}


class MarketPerformanceAccumulatedOut(BaseModel):
    brand_id: int
    brand_name: str
    molecule_name: str
    period_type: str
    ref_date: date
    units: int | None
    market_share: float | None

    model_config = {"from_attributes": True}


# --- Recetas ---


class PrescriptionOut(BaseModel):
    brand_id: int
    brand_name: str
    month: date
    prescriptions: int
    physicians: int

    model_config = {"from_attributes": True}


class PrescriptionMarketShareOut(BaseModel):
    brand_id: int
    brand_name: str
    month: date
    sie_prescriptions: int | None
    market_prescriptions: int | None
    market_share: float | None

    model_config = {"from_attributes": True}


class PrescriptionCompetitorOut(BaseModel):
    sie_brand_name: str
    competitor_brand_name: str
    month: date
    prescriptions: int

    model_config = {"from_attributes": True}


# --- Canales ---


class ChannelDistributionOut(BaseModel):
    brand_id: int
    brand_name: str
    units: int
    conversion_pct: float | None
    counter_pct: float | None

    model_config = {"from_attributes": True}


# --- Convenios ---


class AgreementOut(BaseModel):
    brand_id: int
    brand_name: str
    health_plan: str
    units_current: int | None
    units_previous: int | None
    delta_pct: int | None
    net_amount: float | None

    model_config = {"from_attributes": True}


# --- Precios ---


class PriceOut(BaseModel):
    brand_id: int
    brand_name: str
    presentation: str
    laboratory: str
    product_name: str
    pvp_previous: float | None
    pvp_current: float | None
    variation: float | None
    is_siegfried: bool

    model_config = {"from_attributes": True}


# --- Stock ---


class StockBrandOut(BaseModel):
    brand_id: int
    brand_name: str
    month: date
    days_cover: int | None
    sales: int | None
    stock_units: int | None

    model_config = {"from_attributes": True}


class StockPresentationOut(BaseModel):
    presentation_id: int
    presentation_name: str
    brand_name: str
    familia: str | None
    month: date
    sales: int | None
    days_cover: int | None
    status: str | None

    model_config = {"from_attributes": True}


# --- KPIs ---


class KpiGlobalOut(BaseModel):
    id: int
    loaded_at: datetime
    data: dict

    model_config = {"from_attributes": True}


class KpiBrandOut(BaseModel):
    brand_id: int
    brand_name: str
    loaded_at: datetime
    data: dict

    model_config = {"from_attributes": True}
