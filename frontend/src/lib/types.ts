/* Types matching backend Pydantic response schemas */

/* ── Catálogos ──────────────────────────────────────────────────── */

export interface Brand {
  id: number;
  name: string;
  molecule_id: number | null;
  molecule_name: string | null;
  manufacturer: string | null;
  is_siegfried: boolean;
  color: string | null;
}

export interface Molecule {
  id: number;
  name: string;
  clase: string | null;
}

/* ── Budget ─────────────────────────────────────────────────────── */

export interface BudgetEntry {
  brand_id: number;
  brand_name: string;
  year: number;
  month: number;
  budget: number | null;
  actual: number | null;
}

/* ── Market Performance ─────────────────────────────────────────── */

export interface MarketPerformance {
  brand_id: number;
  brand_name: string;
  molecule_name: string;
  month: string; // "2025-01-01"
  units: number | null;
  market_share: number | null;
}

/* ── Recetas ────────────────────────────────────────────────────── */

export interface Prescription {
  brand_id: number;
  brand_name: string;
  month: string;
  prescriptions: number;
  physicians: number;
}

export interface PrescriptionMS {
  brand_id: number;
  brand_name: string;
  month: string;
  sie_prescriptions: number | null;
  market_prescriptions: number | null;
  market_share: number | null;
}

export interface PrescriptionCompetitor {
  sie_brand_name: string;
  competitor_brand_name: string;
  month: string;
  prescriptions: number;
}

/* ── Canales ────────────────────────────────────────────────────── */

export interface Channel {
  brand_id: number;
  brand_name: string;
  units: number;
  conversion_pct: number | null;
  counter_pct: number | null;
}

/* ── Convenios ──────────────────────────────────────────────────── */

export interface Agreement {
  brand_id: number;
  brand_name: string;
  health_plan: string;
  units_current: number | null;
  units_previous: number | null;
  delta_pct: number | null;
  net_amount: number | null;
}

/* ── Precios ────────────────────────────────────────────────────── */

export interface Price {
  brand_id: number;
  brand_name: string;
  presentation: string;
  laboratory: string;
  product_name: string;
  pvp_previous: number | null;
  pvp_current: number | null;
  variation: number | null;
  is_siegfried: boolean;
}

/* ── Stock ──────────────────────────────────────────────────────── */

export interface StockBrand {
  brand_id: number;
  brand_name: string;
  month: string;
  days_cover: number | null;
  sales: number | null;
  stock_units: number | null;
}

export interface StockPresentation {
  presentation_id: number;
  presentation_name: string;
  brand_name: string;
  familia: string | null;
  month: string;
  sales: number | null;
  days_cover: number | null;
  status: string | null;
}

/* ── KPIs ───────────────────────────────────────────────────────── */

export interface KpiGlobal {
  id: number;
  loaded_at: string;
  data: Record<string, number | string>;
}

export interface KpiBrand {
  brand_id: number;
  brand_name: string;
  loaded_at: string;
  data: Record<string, number | string>;
}

/* ── DDD ────────────────────────────────────────────────────────── */

export interface DddMarket {
  id: number;
  name: string;
  clase: string | null;
  total_units: number | null;
  sie_units: number | null;
  global_ms: number | null;
}

export interface DddBrand {
  id: number;
  name: string;
  is_siegfried: boolean;
}

export interface DddBrandMonthly {
  ddd_brand_id: number;
  brand_name: string;
  region_name: string;
  month: number;
  units: number | null;
}

export interface DddTotalMonthly {
  market_id: number;
  region_name: string;
  month: number;
  units: number | null;
}

export interface DddMarketDetail {
  market: DddMarket;
  brands: DddBrand[];
  brand_monthly: DddBrandMonthly[];
  total_monthly: DddTotalMonthly[];
}

export interface DddRegion {
  market_id: number;
  region_name: string;
  total_units: number | null;
  sie_units: number | null;
  market_share: number | null;
}
