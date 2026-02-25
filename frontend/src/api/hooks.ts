import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { QUERY_STALE_TIME } from "@/lib/constants";
import type {
  Brand,
  BudgetEntry,
  MarketPerformance,
  Prescription,
  PrescriptionMS,
  PrescriptionCompetitor,
  Channel,
  Agreement,
  Price,
  StockBrand,
  StockPresentation,
  KpiGlobal,
  KpiBrand,
  DddMarket,
  DddMarketDetail,
  DddRegion,
} from "@/lib/types";

function qs(params: Record<string, string | number | null | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v != null && v !== "",
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(v!)}`).join("&");
}

/* ── Brands ─────────────────────────────────────────────────────── */

export function useBrands() {
  return useQuery<Brand[]>({
    queryKey: ["brands"],
    queryFn: () => apiFetch("/brands"),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Budget ─────────────────────────────────────────────────────── */

export function useBudget(brandId?: number | null, year?: number | null) {
  return useQuery<BudgetEntry[]>({
    queryKey: ["budget", brandId, year],
    queryFn: () =>
      apiFetch(`/budget${qs({ brand_id: brandId, year })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Market Performance ─────────────────────────────────────────── */

export function useMarketPerformance(
  molecule?: string | null,
  year?: number | null,
) {
  return useQuery<MarketPerformance[]>({
    queryKey: ["marketPerformance", molecule, year],
    queryFn: () =>
      apiFetch(
        `/market/performance${qs({ molecule, year })}`,
      ),
    enabled: molecule != null,
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Prescriptions ──────────────────────────────────────────────── */

export function usePrescriptions(brandId?: number | null, year?: number | null) {
  return useQuery<Prescription[]>({
    queryKey: ["prescriptions", brandId, year],
    queryFn: () =>
      apiFetch(`/prescriptions${qs({ brand_id: brandId, year })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

export function usePrescriptionMS(brandId?: number | null) {
  return useQuery<PrescriptionMS[]>({
    queryKey: ["prescriptionMS", brandId],
    queryFn: () =>
      apiFetch(`/prescriptions/market-share${qs({ brand_id: brandId })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

export function usePrescriptionCompetitors(brand?: string | null) {
  return useQuery<PrescriptionCompetitor[]>({
    queryKey: ["prescriptionCompetitors", brand],
    queryFn: () =>
      apiFetch(`/prescriptions/competitors${qs({ brand })}`),
    enabled: brand != null,
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Channels ───────────────────────────────────────────────────── */

export function useChannels() {
  return useQuery<Channel[]>({
    queryKey: ["channels"],
    queryFn: () => apiFetch("/channels"),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Agreements ─────────────────────────────────────────────────── */

export function useAgreements(brandId?: number | null) {
  return useQuery<Agreement[]>({
    queryKey: ["agreements", brandId],
    queryFn: () => apiFetch(`/agreements${qs({ brand_id: brandId })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Prices ─────────────────────────────────────────────────────── */

export function usePrices(brand?: string | null) {
  return useQuery<Price[]>({
    queryKey: ["prices", brand],
    queryFn: () => apiFetch(`/prices${qs({ brand })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── Stock ──────────────────────────────────────────────────────── */

export function useStockBrands(brandId?: number | null, year?: number | null) {
  return useQuery<StockBrand[]>({
    queryKey: ["stockBrands", brandId, year],
    queryFn: () =>
      apiFetch(`/stock/brands${qs({ brand_id: brandId, year })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

export function useStockPresentations(brandId?: number | null, status?: string | null) {
  return useQuery<StockPresentation[]>({
    queryKey: ["stockPresentations", brandId, status],
    queryFn: () =>
      apiFetch(`/stock/presentations${qs({ brand_id: brandId, status })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── KPIs ───────────────────────────────────────────────────────── */

export function useKpiGlobal() {
  return useQuery<KpiGlobal | null>({
    queryKey: ["kpiGlobal"],
    queryFn: () => apiFetch("/kpis/global"),
    staleTime: QUERY_STALE_TIME,
  });
}

export function useKpiBrands(brandId?: number | null) {
  return useQuery<KpiBrand[]>({
    queryKey: ["kpiBrands", brandId],
    queryFn: () => apiFetch(`/kpis/brands${qs({ brand_id: brandId })}`),
    staleTime: QUERY_STALE_TIME,
  });
}

/* ── DDD ────────────────────────────────────────────────────────── */

export function useDddMarkets() {
  return useQuery<DddMarket[]>({
    queryKey: ["dddMarkets"],
    queryFn: () => apiFetch("/ddd/markets"),
    staleTime: QUERY_STALE_TIME,
  });
}

export function useDddMarketDetail(
  marketId: number | null,
  regionIds?: number[],
) {
  const regionParam =
    regionIds && regionIds.length > 0
      ? "?" + regionIds.map((id) => `region_id=${id}`).join("&")
      : "";
  return useQuery<DddMarketDetail>({
    queryKey: ["dddMarketDetail", marketId, regionIds],
    queryFn: () =>
      apiFetch(`/ddd/markets/${marketId}/brands${regionParam}`),
    enabled: marketId != null,
    staleTime: QUERY_STALE_TIME,
  });
}

export function useDddRegions(marketId: number | null, sortBy?: string) {
  return useQuery<DddRegion[]>({
    queryKey: ["dddRegions", marketId, sortBy],
    queryFn: () =>
      apiFetch(`/ddd/markets/${marketId}/regions${qs({ sort_by: sortBy })}`),
    enabled: marketId != null,
    staleTime: QUERY_STALE_TIME,
  });
}
