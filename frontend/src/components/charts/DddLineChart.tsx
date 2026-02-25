import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { formatCompact } from "@/lib/formatters";

interface DddPoint {
  month: string;
  units: number;
}

interface DddLineChartProps {
  data: DddPoint[];
  brandName: string;
  color: string;
}

export default function DddLineChart({
  data,
  brandName,
  color,
}: DddLineChartProps) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold" style={{ color }}>
        {brandName}
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => formatCompact(v)}
          />
          <Tooltip
            formatter={(value: number) => [formatCompact(value), "Unidades"]}
            contentStyle={{ fontSize: 11, borderRadius: 8 }}
          />
          <Line
            type="monotone"
            dataKey="units"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 2 }}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
