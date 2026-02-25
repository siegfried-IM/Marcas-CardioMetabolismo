import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { MONTHS_ES, CHART_PALETTE } from "@/lib/constants";
import { formatCompact } from "@/lib/formatters";
import type { MarketPerformance } from "@/lib/types";

interface PerformanceChartProps {
  data: MarketPerformance[];
  brandColors?: Record<string, string>;
}

export default function PerformanceChart({
  data,
  brandColors = {},
}: PerformanceChartProps) {
  const brands = [...new Set(data.map((d) => d.brand_name))];
  const monthMap = new Map<string, Record<string, number>>();

  for (const d of data) {
    if (!monthMap.has(d.month)) {
      monthMap.set(d.month, {});
    }
    monthMap.get(d.month)![d.brand_name] = d.units ?? 0;
  }

  const chartData = [...monthMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, values]) => {
      const parts = month.split("-");
      const monthIdx = parseInt(parts[1]!, 10) - 1;
      return {
        month: MONTHS_ES[monthIdx] ?? month,
        ...values,
      };
    });

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart
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
          tick={{ fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCompact(v)}
        />
        <Tooltip
          formatter={(value: number) => [formatCompact(value), ""]}
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {brands.map((brand, idx) => (
          <Line
            key={brand}
            type="monotone"
            dataKey={brand}
            stroke={
              brandColors[brand] ?? CHART_PALETTE[idx % CHART_PALETTE.length]
            }
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
