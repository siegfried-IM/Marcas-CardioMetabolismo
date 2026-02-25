interface SegmentControlProps<T extends string> {
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
}

export default function SegmentControl<T extends string>({
  options,
  value,
  onChange,
}: SegmentControlProps<T>) {
  return (
    <div className="inline-flex rounded-lg bg-neutral-100 p-0.5">
      {options.map((opt) => {
        const isActive = opt === value;
        return (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={[
              "rounded-md px-4 py-1.5 text-xs font-semibold transition-all",
              isActive
                ? "bg-sie text-white shadow-sm"
                : "text-neutral-500 hover:text-neutral-700",
            ].join(" ")}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}
