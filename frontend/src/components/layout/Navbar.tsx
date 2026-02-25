import { NavLink } from "react-router";

const links = [
  { to: "/", label: "Hub" },
  { to: "/cardio", label: "Cardio" },
  { to: "/cardio/ddd", label: "DDD" },
] as const;

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 flex h-[50px] items-center border-b-2 border-sie bg-white px-6 shadow-sm">
      {/* Logo */}
      <NavLink to="/" className="mr-8 flex items-center gap-1.5 no-underline">
        <span className="font-mono text-lg font-bold tracking-wider text-sie-dark">
          SIEGFRIED
        </span>
        <span className="text-xs font-medium tracking-wide text-neutral-400">
          BI
        </span>
      </NavLink>

      {/* Tab links */}
      <div className="flex h-full items-stretch gap-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              [
                "flex items-center px-4 text-sm font-medium transition-colors",
                isActive
                  ? "border-b-2 border-sie text-sie-dark"
                  : "border-b-2 border-transparent text-neutral-500 hover:text-neutral-800",
              ].join(" ")
            }
          >
            {link.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
