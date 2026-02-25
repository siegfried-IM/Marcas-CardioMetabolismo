/** Siegfried brand color palette */
export const BRAND_COLORS = {
  sie: "#B01E1E",
  sieDark: "#7A1518",
  sieDeep: "#5C1010",
  sieLight: "#F9E8E8",
  sieMuted: "#D4A0A0",
} as const;

/** Extended chart palette for multi-series charts */
export const CHART_PALETTE = [
  "#B01E1E",
  "#2563EB",
  "#16A34A",
  "#D97706",
  "#7C3AED",
  "#DB2777",
  "#0891B2",
  "#4F46E5",
  "#059669",
  "#DC2626",
] as const;

/** Base URL for API requests — proxied by Vite in dev */
export const API_BASE_URL = "/api/v1";

/** Default stale time for TanStack Query (5 minutes) */
export const QUERY_STALE_TIME = 5 * 60 * 1000;

/** Months abbreviation in Spanish */
export const MONTHS_ES = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic",
] as const;
