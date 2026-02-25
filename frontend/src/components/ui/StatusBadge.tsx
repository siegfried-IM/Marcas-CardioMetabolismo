const STATUS_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  ok: { bg: "bg-green-100", text: "text-green-800", label: "OK" },
  alerta: { bg: "bg-yellow-100", text: "text-yellow-800", label: "Alerta" },
  bajo: { bg: "bg-orange-100", text: "text-orange-800", label: "Bajo" },
  quiebre: { bg: "bg-red-100", text: "text-red-800", label: "Quiebre" },
};

const DEFAULT_CONFIG = { bg: "bg-neutral-100", text: "text-neutral-600", label: "" };

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { ...DEFAULT_CONFIG, label: status };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${config.bg} ${config.text}`}
    >
      {config.label}
    </span>
  );
}
