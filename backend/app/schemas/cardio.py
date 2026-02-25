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
    billing: float | None = None

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
    stock_units: int | None = None
    billing: float | None = None

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


# --- Convenios Detalle ---


class AgreementDetailOut(BaseModel):
    id: int
    brand_id: int | None
    brand_name: str | None = None
    laboratory: str | None
    line: str | None
    familia: str | None
    health_plan: str
    health_plan_detail: str | None
    product_name: str | None
    units: int | None
    pvp_amount: float | None
    system_coverage: float | None
    lab_pvp_contribution: float | None
    lab_adjustment: float | None
    lab_total_contribution: float | None
    net_contribution: float | None
    report_date: date | None

    model_config = {"from_attributes": True}


# --- Mercado Regional ---


class MarketPerformanceRegionalOut(BaseModel):
    id: int
    brand_id: int | None
    brand_name: str | None = None
    molecule_name: str | None = None
    region_name: str | None = None
    month: date
    units: int | None

    model_config = {"from_attributes": True}


# --- ATENEO Regional ---


class MarketAteneoOut(BaseModel):
    id: int
    atc_code: str | None
    region: str | None
    brand_name: str | None
    product_name: str | None
    laboratory: str | None
    product_code: str | None
    mat_5: int | None
    mat_4: int | None
    mat_3: int | None
    mat_2: int | None
    mat_current: int | None
    mes_12: int | None
    mes_11: int | None
    mes_10: int | None
    mes_9: int | None
    mes_8: int | None
    mes_7: int | None
    mes_6: int | None
    mes_5: int | None
    mes_4: int | None
    mes_3: int | None
    mes_2: int | None
    mes_current: int | None
    ytd_5: int | None
    ytd_4: int | None
    ytd_3: int | None
    ytd_2: int | None
    ytd_current: int | None
    ref_date: date | None

    model_config = {"from_attributes": True}


# --- ATENEO Nacional ---


class MarketAteneoNationalOut(BaseModel):
    id: int
    pack_code: str | None
    pack_name: str | None
    product_name: str | None
    corporation: str | None
    manufacturer: str | None
    atc_iv: str | None
    molecule: str | None
    pharma_form: str | None
    launch_date: str | None
    market_type: str | None
    period_type: str
    period_date: date
    usd_amount: float | None
    local_amount: float | None
    units: int | None

    model_config = {"from_attributes": True}


# --- Catalogo Precios ---


class PriceCatalogOut(BaseModel):
    id: int
    registro: str | None
    troquel: str | None
    product_name: str | None
    presentation: str | None
    drug_name: str | None
    pharma_action: str | None
    laboratory: str | None
    barcode: str | None
    product_type: str | None
    pami_category: str | None
    status: str | None
    qty_presentations: int | None
    pvp_previous: float | None
    pvp_current: float | None
    variation_pct: float | None
    effective_date: date | None
    pvp_previous_date: date | None
    pvp_current_date: date | None

    model_config = {"from_attributes": True}
