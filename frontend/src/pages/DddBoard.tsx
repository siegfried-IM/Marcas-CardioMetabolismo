import { useEffect, useMemo, useRef, useState } from "react";
import { useDddFilters } from "@/stores/dddFilters";
import {
  useDddMarkets,
  useDddMarketDetail,
  useDddRegions,
} from "@/api/hooks";
import { CHART_PALETTE, BRAND_COLORS, MONTHS_ES } from "@/lib/constants";
import { formatNumber, formatPct, formatCompact } from "@/lib/formatters";
import type { Column } from "@/components/ui/DataTable";
import type { DddRegion } from "@/lib/types";

import KpiCard from "@/components/ui/KpiCard";
import PillSelector from "@/components/ui/PillSelector";
import DddLineChart from "@/components/charts/DddLineChart";
import DataTable from "@/components/ui/DataTable";

export default function DddBoard() {
  const {
    activeMarketId,
    setActiveMarketId,
    selectedRegionIds,
    toggleRegionId,
    clearRegions,
  } = useDddFilters();

  const { data: markets } = useDddMarkets();
  const { data: detail } = useDddMarketDetail(activeMarketId, selectedRegionIds);
  const { data: regions } = useDddRegions(activeMarketId);

  // Auto-select first market
  useEffect(() => {
    if (activeMarketId == null && markets && markets.length > 0) {
      setActiveMarketId(markets[0]!.id);
    }
  }, [activeMarketId, markets, setActiveMarketId]);

  const market = detail?.market ?? null;

  /* --- market pill items --- */
  const marketPills = (markets ?? []).map((m, idx) => ({
    id: String(m.id),
    label: m.name,
    color: CHART_PALETTE[idx % CHART_PALETTE.length]!,
  }));

  /* --- group brand_monthly data for line charts --- */
  const brandGroups = useMemo(() => {
    if (!detail?.brands || !detail.brand_monthly) return [];

    const brandMap = new Map(detail.brands.map((b) => [b.id, b]));
    const dataMap = new Map<number, { month: number; units: number | null }[]>();

    for (const bm of detail.brand_monthly) {
      const arr = dataMap.get(bm.ddd_brand_id) ?? [];
      arr.push({ month: bm.month, units: bm.units });
      dataMap.set(bm.ddd_brand_id, arr);
    }

    return [...dataMap.entries()].map(([brandId, items], idx) => {
      const brand = brandMap.get(brandId);
      return {
        brandName: brand?.name ?? `Marca ${brandId}`,
        isSiegfried: brand?.is_siegfried ?? false,
        color: brand?.is_siegfried
          ? BRAND_COLORS.sie
          : (CHART_PALETTE[(idx + 1) % CHART_PALETTE.length] ?? "#666"),
        data: items
          .sort((a, b) => a.month - b.month)
          .map((d) => ({
            month: MONTHS_ES[d.month - 1] ?? String(d.month),
            units: d.units ?? 0,
          })),
      };
    });
  }, [detail]);

  /* --- region multi-select dropdown --- */
  const [regionDropdownOpen, setRegionDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setRegionDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  /* --- region table columns --- */
  const regionCols: Column<DddRegion>[] = [
    {
      key: "region_name",
      header: "Region",
      render: (r) => <span className="font-medium">{r.region_name}</span>,
      sortValue: (r) => r.region_name,
    },
    {
      key: "total_units",
      header: "Unidades totales",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatNumber(r.total_units)}</span>
      ),
      sortValue: (r) => r.total_units ?? 0,
    },
    {
      key: "sie_units",
      header: "Unidades SIE",
      align: "right",
      render: (r) => (
        <span className="font-num text-[var(--color-sie)]">
          {formatNumber(r.sie_units)}
        </span>
      ),
      sortValue: (r) => r.sie_units ?? 0,
    },
    {
      key: "market_share",
      header: "MS SIE %",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatPct(r.market_share)}</span>
      ),
      sortValue: (r) => r.market_share ?? 0,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-neutral-800">
          DDD &mdash; Dosis Diaria Definida
        </h1>
        <p className="text-sm text-neutral-500">
          Analisis por mercado, marca y region
        </p>
      </div>

      {/* Market selector pills */}
      <PillSelector
        items={marketPills}
        activeId={activeMarketId != null ? String(activeMarketId) : null}
        onSelect={(id) => setActiveMarketId(Number(id))}
      />

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard
          label="Unidades totales"
          value={formatCompact(market?.total_units)}
          accentColor="#2563eb"
        />
        <KpiCard
          label="Unidades SIE"
          value={formatCompact(market?.sie_units)}
          accentColor={BRAND_COLORS.sie}
        />
        <KpiCard
          label="MS Global SIE"
          value={market?.global_ms != null ? `${market.global_ms}%` : "\u2014"}
          accentColor="#16a34a"
        />
        <KpiCard
          label="Marcas"
          value={detail?.brands ? String(detail.brands.length) : "\u2014"}
          accentColor="#7c3aed"
        />
      </div>

      {/* Region multi-select dropdown */}
      {regions && regions.length > 0 && (
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setRegionDropdownOpen((o) => !o)}
            className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 shadow-sm hover:border-neutral-400"
          >
            Regiones
            {selectedRegionIds.length > 0 && (
              <span className="rounded-full bg-[var(--color-sie)] px-2 py-0.5 text-[10px] font-bold text-white">
                {selectedRegionIds.length}
              </span>
            )}
            <svg
              className={`h-4 w-4 transition-transform ${regionDropdownOpen ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {regionDropdownOpen && (
            <div className="absolute z-30 mt-1 max-h-72 w-64 overflow-y-auto rounded-lg border border-neutral-200 bg-white py-1 shadow-lg">
              <button
                onClick={clearRegions}
                className="w-full px-3 py-1.5 text-left text-xs text-neutral-500 hover:bg-neutral-50"
              >
                Limpiar seleccion
              </button>
              <hr className="my-1 border-neutral-100" />
              {regions.map((r, i) => {
                const checked = selectedRegionIds.includes(i);
                return (
                  <label
                    key={r.region_name}
                    className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-neutral-50"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleRegionId(i)}
                      className="h-3.5 w-3.5 rounded border-neutral-300"
                    />
                    {r.region_name}
                  </label>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Brand line charts */}
      {brandGroups.length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-neutral-800">
            Unidades mensuales por marca
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            {brandGroups.map((bg) => (
              <DddLineChart
                key={bg.brandName}
                brandName={bg.brandName}
                color={bg.color}
                data={bg.data}
              />
            ))}
          </div>
        </div>
      )}

      {/* Regional summary table */}
      {regions && regions.length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-neutral-800">
            Resumen regional
          </h2>
          <DataTable
            columns={regionCols}
            data={regions}
            rowKey={(r) => r.region_name}
          />
        </div>
      )}

      {/* Empty state when no market selected */}
      {!activeMarketId && (
        <div className="flex items-center justify-center py-16 text-sm text-neutral-400">
          Seleccione un mercado para ver los datos
        </div>
      )}
    </div>
  );
}
