import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { MONTHS_ES, BRAND_COLORS } from "@/lib/constants";
import { formatCompact, formatNumber } from "@/lib/formatters";
import type { StockBrand } from "@/lib/types";

interface StockChartProps {
  data: StockBrand[];
}

export default function StockChart({ data }: StockChartProps) {
  const chartData = data.map((d) => {
    const parts = d.month.split("-");
    const monthIdx = parseInt(parts[1]!, 10) - 1;
    return {
      month: MONTHS_ES[monthIdx] ?? d.month,
      sales: d.sales ?? 0,
      stock_units: d.stock_units ?? 0,
      days_cover: d.days_cover ?? 0,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart
        data={chartData}
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
          yAxisId="units"
          tick={{ fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCompact(v)}
        />
        <YAxis
          yAxisId="days"
          orientation="right"
          tick={{ fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${formatNumber(v)}d`}
        />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === "days_cover")
              return [`${formatNumber(value)} dias`, "Cobertura"];
            return [
              formatCompact(value),
              name === "sales" ? "Ventas" : "Stock",
            ];
          }}
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Legend
          formatter={(value: string) => {
            if (value === "sales") return "Ventas";
            if (value === "stock_units") return "Stock";
            return "Cobertura (dias)";
          }}
          wrapperStyle={{ fontSize: 12 }}
        />
        <Bar
          yAxisId="units"
          dataKey="sales"
          fill={BRAND_COLORS.sie}
          radius={[4, 4, 0, 0]}
          maxBarSize={28}
          opacity={0.8}
        />
        <Bar
          yAxisId="units"
          dataKey="stock_units"
          fill="#94a3b8"
          radius={[4, 4, 0, 0]}
          maxBarSize={28}
          opacity={0.6}
        />
        <Line
          yAxisId="days"
          type="monotone"
          dataKey="days_cover"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
