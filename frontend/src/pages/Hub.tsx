import { Link } from "react-router";

interface LineCard {
  title: string;
  description: string;
  to: string;
  enabled: boolean;
}

const LINES: LineCard[] = [
  {
    title: "Cardio-Metabolismo",
    description: "Gestión de marcas, presupuesto, market share, recetas y stock",
    to: "/cardio",
    enabled: true,
  },
  {
    title: "Antibioticos",
    description: "Dashboards de la linea de antibioticos",
    to: "#",
    enabled: false,
  },
  {
    title: "Respiratoria",
    description: "Dashboards de la linea respiratoria",
    to: "#",
    enabled: false,
  },
  {
    title: "Dermatologia",
    description: "Dashboards de la linea de dermatologia",
    to: "#",
    enabled: false,
  },
  {
    title: "Ginecologia",
    description: "Dashboards de la linea de ginecologia",
    to: "#",
    enabled: false,
  },
  {
    title: "Traumatologia",
    description: "Dashboards de la linea de traumatologia",
    to: "#",
    enabled: false,
  },
];

export default function Hub() {
  return (
    <div>
      {/* Hero */}
      <div className="mb-8 rounded-2xl bg-gradient-to-br from-sie-dark to-sie-deep px-8 py-12 text-white shadow-lg">
        <p className="mb-1 font-mono text-sm tracking-widest text-white/60 uppercase">
          Siegfried BI
        </p>
        <h1 className="mb-3 text-3xl font-bold tracking-tight">
          Marketing Intelligence
        </h1>
        <p className="max-w-xl text-sm leading-relaxed text-white/80">
          Plataforma centralizada de indicadores comerciales, market share,
          recetas medicas, stock y presupuesto para todas las lineas terapeuticas
          de Siegfried.
        </p>
      </div>

      {/* Lines grid */}
      <h2 className="mb-4 text-lg font-semibold text-neutral-800">
        Lineas terapeuticas
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {LINES.map((line) => {
          const content = (
            <div
              className={[
                "group relative overflow-hidden rounded-xl border bg-white p-5 shadow-sm transition-all",
                line.enabled
                  ? "cursor-pointer border-transparent hover:border-sie hover:shadow-md"
                  : "cursor-default border-neutral-200 opacity-50",
              ].join(" ")}
            >
              {/* Accent top bar */}
              <div
                className={`absolute left-0 top-0 h-1 w-full ${
                  line.enabled ? "bg-sie" : "bg-neutral-300"
                }`}
              />

              <h3 className="mb-1 text-base font-semibold text-neutral-800 group-hover:text-sie-dark">
                {line.title}
              </h3>
              <p className="text-xs leading-relaxed text-neutral-500">
                {line.description}
              </p>

              {line.enabled && (
                <span className="mt-3 inline-block text-xs font-medium text-sie">
                  Abrir dashboard &rarr;
                </span>
              )}
              {!line.enabled && (
                <span className="mt-3 inline-block text-[10px] font-medium tracking-wide text-neutral-400 uppercase">
                  Proximamente
                </span>
              )}
            </div>
          );

          if (line.enabled) {
            return (
              <Link key={line.title} to={line.to} className="no-underline">
                {content}
              </Link>
            );
          }
          return <div key={line.title}>{content}</div>;
        })}
      </div>
    </div>
  );
}
