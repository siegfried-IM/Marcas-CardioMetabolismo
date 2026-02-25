import { useEffect, useMemo } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useCardioFilters } from "@/stores/cardioFilters";
import {
  useBrands,
  useKpiGlobal,
  useBudget,
  useMarketPerformance,
  usePrescriptions,
  usePrescriptionMS,
  usePrescriptionCompetitors,
  useChannels,
  useAgreements,
  usePrices,
  useStockBrands,
  useStockPresentations,
} from "@/api/hooks";
import { BRAND_COLORS, CHART_PALETTE, MONTHS_ES } from "@/lib/constants";
import {
  formatNumber,
  formatPct,
  formatCurrency,
  formatCompact,
} from "@/lib/formatters";
import type { Column } from "@/components/ui/DataTable";
import type { Agreement, Price, StockPresentation, PrescriptionCompetitor } from "@/lib/types";

import Section from "@/components/layout/Section";
import KpiCard from "@/components/ui/KpiCard";
import PillSelector from "@/components/ui/PillSelector";
import SegmentControl from "@/components/ui/SegmentControl";
import DataTable from "@/components/ui/DataTable";
import StatusBadge from "@/components/ui/StatusBadge";
import BudgetChart from "@/components/charts/BudgetChart";
import PerformanceChart from "@/components/charts/PerformanceChart";
import StockChart from "@/components/charts/StockChart";

export default function CardioBoard() {
  const {
    activeBrand,
    setActiveBrand,
    period,
    setPeriod,
    year,
    molecule,
    setMolecule,
  } = useCardioFilters();

  /* --- data hooks --- */
  const { data: brands } = useBrands();
  const sieBrands = useMemo(
    () => (brands ?? []).filter((b) => b.is_siegfried),
    [brands],
  );

  // Auto-select first brand
  useEffect(() => {
    if (!activeBrand && sieBrands.length > 0) {
      const first = sieBrands[0]!;
      setActiveBrand(first.name);
      if (first.molecule_name) setMolecule(first.molecule_name);
    }
  }, [activeBrand, sieBrands, setActiveBrand, setMolecule]);

  const selectedBrand = useMemo(
    () => sieBrands.find((b) => b.name === activeBrand) ?? null,
    [sieBrands, activeBrand],
  );

  const brandId = selectedBrand?.id ?? null;
  const brandColor = selectedBrand?.color ?? BRAND_COLORS.sie;

  const brandColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const b of brands ?? []) {
      if (b.color) map[b.name] = b.color;
    }
    return map;
  }, [brands]);

  const { data: kpiGlobal } = useKpiGlobal();
  const { data: budgetData } = useBudget(brandId, year);
  const { data: perfData } = useMarketPerformance(molecule, year);
  const { data: rxData } = usePrescriptions(brandId, year);
  const { data: rxMsData } = usePrescriptionMS(brandId);
  const { data: rxCompData } = usePrescriptionCompetitors(activeBrand);
  const { data: channelData } = useChannels();
  const { data: agreementsData } = useAgreements(brandId);
  const { data: pricesData } = usePrices(activeBrand);
  const { data: stockBrandsData } = useStockBrands(brandId, year);
  const { data: stockPresData } = useStockPresentations(brandId);

  /* --- KPI data from JSONB --- */
  const kpiData = kpiGlobal?.data;
  const kpiKey = (key: string) =>
    period === "MAT" ? `${key.replace("_ytd", "_mat")}` : key;

  /* --- brand pill items --- */
  const pillItems = sieBrands.map((b) => ({
    id: b.name,
    label: b.name,
    color: b.color ?? BRAND_COLORS.sie,
  }));

  const handleBrandSelect = (name: string) => {
    setActiveBrand(name);
    const brand = sieBrands.find((b) => b.name === name);
    if (brand?.molecule_name) setMolecule(brand.molecule_name);
  };

  /* --- prescription line chart data --- */
  const rxChartData = useMemo(() => {
    if (!rxData) return [];
    return rxData.map((d) => {
      const parts = d.month.split("-");
      const monthIdx = parseInt(parts[1]!, 10) - 1;
      return {
        month: MONTHS_ES[monthIdx] ?? d.month,
        prescriptions: d.prescriptions,
        physicians: d.physicians,
      };
    });
  }, [rxData]);

  /* --- prescription MS bar chart data --- */
  const rxMsChartData = useMemo(() => {
    if (!rxMsData) return [];
    const latestMonth = rxMsData.reduce(
      (max, d) => (d.month > max ? d.month : max),
      "",
    );
    return rxMsData
      .filter((d) => d.month === latestMonth && d.market_share != null)
      .sort((a, b) => (b.market_share ?? 0) - (a.market_share ?? 0));
  }, [rxMsData]);

  /* --- channel pie data --- */
  const channelPieData = useMemo(() => {
    if (!channelData) return [];
    return channelData
      .filter((d) => d.brand_name === activeBrand)
      .flatMap((d) => [
        { name: "Convenios", value: d.conversion_pct ?? 0, fill: CHART_PALETTE[0] },
        { name: "Mostrador", value: d.counter_pct ?? 0, fill: CHART_PALETTE[1] },
      ]);
  }, [channelData, activeBrand]);

  /* --- agreement table columns --- */
  const agreementCols: Column<Agreement>[] = [
    {
      key: "health_plan",
      header: "Obra Social",
      render: (r) => <span className="font-medium">{r.health_plan}</span>,
      sortValue: (r) => r.health_plan,
    },
    {
      key: "units_current",
      header: "Unid. 2025",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatNumber(r.units_current)}</span>
      ),
      sortValue: (r) => r.units_current ?? 0,
    },
    {
      key: "units_previous",
      header: "Unid. 2024",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatNumber(r.units_previous)}</span>
      ),
      sortValue: (r) => r.units_previous ?? 0,
    },
    {
      key: "delta_pct",
      header: "Delta %",
      align: "right",
      render: (r) => (
        <span
          className={`font-num ${(r.delta_pct ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}
        >
          {r.delta_pct != null ? `${r.delta_pct}%` : "\u2014"}
        </span>
      ),
      sortValue: (r) => r.delta_pct ?? 0,
    },
    {
      key: "net_amount",
      header: "Neto $",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatCurrency(r.net_amount)}</span>
      ),
      sortValue: (r) => r.net_amount ?? 0,
    },
  ];

  /* --- prices table columns --- */
  const priceCols: Column<Price>[] = [
    {
      key: "product_name",
      header: "Producto",
      render: (r) => (
        <span className={r.is_siegfried ? "font-semibold text-[var(--color-sie)]" : ""}>
          {r.product_name}
        </span>
      ),
      sortValue: (r) => r.product_name,
    },
    {
      key: "laboratory",
      header: "Laboratorio",
      render: (r) => r.laboratory,
      sortValue: (r) => r.laboratory,
    },
    {
      key: "presentation",
      header: "Presentacion",
      render: (r) => r.presentation,
      sortValue: (r) => r.presentation,
    },
    {
      key: "pvp_previous",
      header: "PVP Ant.",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatCurrency(r.pvp_previous)}</span>
      ),
      sortValue: (r) => r.pvp_previous ?? 0,
    },
    {
      key: "pvp_current",
      header: "PVP Act.",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatCurrency(r.pvp_current)}</span>
      ),
      sortValue: (r) => r.pvp_current ?? 0,
    },
    {
      key: "variation",
      header: "Var. %",
      align: "right",
      render: (r) => (
        <span
          className={`font-num ${(r.variation ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}
        >
          {r.variation != null ? formatPct(r.variation * 100) : "\u2014"}
        </span>
      ),
      sortValue: (r) => r.variation ?? 0,
    },
  ];

  /* --- stock presentations columns --- */
  const stockPresCols: Column<StockPresentation>[] = [
    {
      key: "presentation_name",
      header: "Presentacion",
      render: (r) => r.presentation_name,
      sortValue: (r) => r.presentation_name,
    },
    {
      key: "sales",
      header: "Ventas",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatNumber(r.sales)}</span>
      ),
      sortValue: (r) => r.sales ?? 0,
    },
    {
      key: "days_cover",
      header: "Cobertura",
      align: "right",
      render: (r) => (
        <span className="font-num">
          {r.days_cover != null ? `${r.days_cover} dias` : "\u2014"}
        </span>
      ),
      sortValue: (r) => r.days_cover ?? 0,
    },
    {
      key: "status",
      header: "Estado",
      align: "center",
      render: (r) => r.status ? <StatusBadge status={r.status} /> : null,
      sortValue: (r) => r.status ?? "",
    },
  ];

  /* --- competitors columns --- */
  const competitorCols: Column<PrescriptionCompetitor>[] = [
    {
      key: "competitor_brand_name",
      header: "Competidor",
      render: (r) => r.competitor_brand_name,
      sortValue: (r) => r.competitor_brand_name,
    },
    {
      key: "prescriptions",
      header: "Recetas",
      align: "right",
      render: (r) => (
        <span className="font-num">{formatNumber(r.prescriptions)}</span>
      ),
      sortValue: (r) => r.prescriptions,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header row: title + controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-neutral-800">
            Cardio-Metabolismo
          </h1>
          <p className="text-sm text-neutral-500">
            Dashboard de gestion de marcas
          </p>
        </div>
        <SegmentControl
          options={["YTD", "MAT"] as const}
          value={period}
          onChange={setPeriod}
        />
      </div>

      {/* Brand pills */}
      <PillSelector
        items={pillItems}
        activeId={activeBrand}
        onSelect={handleBrandSelect}
      />

      {/* KPI Strip */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiCard
          label="IE"
          value={kpiData ? `${kpiData[kpiKey("ie_ytd")] ?? "\u2014"}` : "\u2014"}
          accentColor={brandColor}
        />
        <KpiCard
          label="Market Share"
          value={kpiData ? `${kpiData[kpiKey("ms_ytd")] ?? "\u2014"}%` : "\u2014"}
          accentColor="#2563eb"
        />
        <KpiCard
          label="Unidades"
          value={kpiData ? formatCompact(Number(kpiData[kpiKey("units_ytd")])) : "\u2014"}
          accentColor="#16a34a"
        />
        <KpiCard
          label="MS Recetas"
          value={kpiData?.ms_rec != null ? `${kpiData.ms_rec}%` : "\u2014"}
          accentColor="#7c3aed"
        />
        <KpiCard
          label="Crec. IE"
          value={kpiData?.ie_growth_ytd != null ? `${kpiData.ie_growth_ytd}%` : "\u2014"}
          accentColor="#d97706"
        />
        <KpiCard
          label="Presupuesto"
          value={kpiData?.bud_pct != null ? `${kpiData.bud_pct}%` : "\u2014"}
          subtitle={kpiData?.bud_total != null ? `Total: ${formatCompact(Number(kpiData.bud_total))}` : undefined}
          accentColor="#0891b2"
        />
      </div>

      {/* Section 1: Budget */}
      <Section
        number={1}
        title="Presupuesto"
        subtitle="Presupuesto vs. real por mes"
      >
        {budgetData && budgetData.length > 0 ? (
          <BudgetChart data={budgetData} brandColor={brandColor} />
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 2: Market Performance */}
      <Section
        number={2}
        title="Performance de Mercado"
        subtitle={`Evolucion de unidades por molecula${molecule ? ` (${molecule})` : ""}`}
      >
        {perfData && perfData.length > 0 ? (
          <PerformanceChart data={perfData} brandColors={brandColorMap} />
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 3: Prescriptions */}
      <Section
        number={3}
        title="Recetas Medicas"
        subtitle="Evolucion mensual de prescripciones"
      >
        {rxChartData.length > 0 ? (
          <div className="space-y-4">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={rxChartData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => formatCompact(v)}
                />
                <Tooltip
                  formatter={(value: number) => [
                    formatNumber(value),
                    "Recetas",
                  ]}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Line
                  type="monotone"
                  dataKey="prescriptions"
                  stroke={brandColor}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 4: Prescription Market Share */}
      <Section
        number={4}
        title="Market Share de Recetas"
        subtitle="Participacion por marca (ultimo mes)"
      >
        {rxMsChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={rxMsChartData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="brand_name"
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval={0}
                angle={-30}
                textAnchor="end"
                height={60}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip
                formatter={(value: number) => [formatPct(value), "MS"]}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="market_share" radius={[4, 4, 0, 0]} maxBarSize={36}>
                {rxMsChartData.map((entry, idx) => (
                  <Cell
                    key={entry.brand_id}
                    fill={
                      brandColorMap[entry.brand_name] ??
                      CHART_PALETTE[idx % CHART_PALETTE.length]
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 5: Prescription Competitors */}
      <Section
        number={5}
        title="Competidores - Recetas"
        subtitle="Ranking de marcas competidoras por recetas"
      >
        {rxCompData && rxCompData.length > 0 ? (
          <DataTable
            columns={competitorCols}
            data={rxCompData}
            rowKey={(r) => `${r.competitor_brand_name}-${r.month}`}
          />
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 6: Channels */}
      <Section
        number={6}
        title="Canales"
        subtitle="Distribucion de ventas por canal"
      >
        {channelPieData.length > 0 ? (
          <div className="flex flex-col items-center gap-4 md:flex-row md:justify-center">
            <ResponsiveContainer width={280} height={280}>
              <PieChart>
                <Pie
                  data={channelPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={110}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                  label={({ name, value }: { name: string; value: number }) =>
                    `${name}: ${value.toFixed(1)}%`
                  }
                  labelLine={false}
                >
                  {channelPieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => [formatPct(value), "Participacion"]}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col gap-2">
              {channelPieData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-2 text-sm">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: entry.fill }}
                  />
                  <span className="text-neutral-700">{entry.name}</span>
                  <span className="font-num text-neutral-500">
                    {formatPct(entry.value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 7: Agreements */}
      <Section
        number={7}
        title="Convenios"
        subtitle="Acuerdos con obras sociales"
      >
        {agreementsData && agreementsData.length > 0 ? (
          <DataTable
            columns={agreementCols}
            data={agreementsData}
            rowKey={(r) => `${r.brand_id}-${r.health_plan}`}
          />
        ) : (
          <EmptyState />
        )}
      </Section>

      {/* Section 8: Stock */}
      <Section
        number={8}
        title="Stock y Cobertura"
        subtitle="Evolucion de stock y dias de cobertura"
      >
        <div className="space-y-4">
          {stockBrandsData && stockBrandsData.length > 0 ? (
            <StockChart data={stockBrandsData} />
          ) : (
            <EmptyState />
          )}

          {stockPresData && stockPresData.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-neutral-700">
                Presentaciones
              </h3>
              <DataTable
                columns={stockPresCols}
                data={stockPresData}
                rowKey={(r) => `${r.presentation_id}-${r.month}`}
              />
            </>
          )}
        </div>
      </Section>

      {/* Section 9: Prices */}
      <Section
        number={9}
        title="Precios"
        subtitle="Comparativo SIE vs competidores por presentacion"
      >
        {pricesData && pricesData.length > 0 ? (
          <DataTable
            columns={priceCols}
            data={pricesData}
            rowKey={(r) => `${r.brand_id}-${r.presentation}-${r.product_name}`}
          />
        ) : (
          <EmptyState />
        )}
      </Section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex items-center justify-center py-12 text-sm text-neutral-400">
      Seleccione una marca para ver los datos
    </div>
  );
}
