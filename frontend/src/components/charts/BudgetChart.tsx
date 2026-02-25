import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { MONTHS_ES, BRAND_COLORS } from "@/lib/constants";
import { formatCompact } from "@/lib/formatters";
import type { BudgetEntry } from "@/lib/types";

interface BudgetChartProps {
  data: BudgetEntry[];
  brandColor?: string;
}

export default function BudgetChart({
  data,
  brandColor = BRAND_COLORS.sie,
}: BudgetChartProps) {
  const chartData = data.map((d) => ({
    month: MONTHS_ES[d.month - 1] ?? String(d.month),
    budget: d.budget ?? 0,
    actual: d.actual ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
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
          formatter={(value: number, name: string) => [
            formatCompact(value),
            name === "budget" ? "Presupuesto" : "Real",
          ]}
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Legend
          formatter={(value: string) =>
            value === "budget" ? "Presupuesto" : "Real"
          }
          wrapperStyle={{ fontSize: 12 }}
        />
        <Bar
          dataKey="budget"
          fill="#d4d4d8"
          radius={[4, 4, 0, 0]}
          maxBarSize={32}
        />
        <Bar
          dataKey="actual"
          fill={brandColor}
          radius={[4, 4, 0, 0]}
          maxBarSize={32}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
