/**
 * Format a number with thousand separators (locale es-AR).
 * Returns "—" for null/undefined.
 */
export function formatNumber(
  value: number | null | undefined,
  decimals = 0,
): string {
  if (value == null) return "—";
  return value.toLocaleString("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format a value as percentage.
 * Expects the value to be already in 0–100 range (e.g. 45.2 → "45,2 %").
 */
export function formatPct(
  value: number | null | undefined,
  decimals = 1,
): string {
  if (value == null) return "—";
  return `${value.toLocaleString("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} %`;
}

/**
 * Format a value as ARS currency.
 */
export function formatCurrency(
  value: number | null | undefined,
  decimals = 0,
): string {
  if (value == null) return "—";
  return value.toLocaleString("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Compact number formatter (e.g. 1.500.000 → "1,5 M").
 */
export function formatCompact(value: number | null | undefined): string {
  if (value == null) return "—";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} M`;
  }
  if (abs >= 1_000) {
    return `${(value / 1_000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} K`;
  }
  return formatNumber(value);
}
