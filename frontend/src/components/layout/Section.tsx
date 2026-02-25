import type { ReactNode } from "react";

interface SectionProps {
  number: number;
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export default function Section({
  number,
  title,
  subtitle,
  children,
}: SectionProps) {
  return (
    <section
      id={`section-${number}`}
      className="scroll-mt-16 rounded-xl bg-white p-5 shadow-sm"
    >
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sie text-xs font-bold text-white">
          {number}
        </span>
        <div>
          <h2 className="text-base font-semibold text-neutral-800">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-0.5 text-xs text-neutral-500">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Content */}
      {children}
    </section>
  );
}
