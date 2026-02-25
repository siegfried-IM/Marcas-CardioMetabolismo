interface KpiCardProps {
  label: string;
  value: string;
  subtitle?: string;
  accentColor?: string;
}

export default function KpiCard({
  label,
  value,
  subtitle,
  accentColor = "#B01E1E",
}: KpiCardProps) {
  return (
    <div className="relative overflow-hidden rounded-lg bg-white p-4 shadow-sm">
      {/* Accent bar */}
      <div
        className="absolute left-0 top-0 h-full w-1"
        style={{ backgroundColor: accentColor }}
      />

      <p className="mb-1 text-xs font-medium tracking-wide text-neutral-500 uppercase">
        {label}
      </p>
      <p
        className="font-num text-xl font-semibold text-neutral-900"
        style={{ color: accentColor }}
      >
        {value}
      </p>
      {subtitle && (
        <p className="mt-1 text-[11px] text-neutral-400">{subtitle}</p>
      )}
    </div>
  );
}
