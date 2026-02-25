import { useState, useMemo, type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => number | string;
  align?: "left" | "center" | "right";
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string | number;
  emptyMessage?: string;
}

type SortDir = "asc" | "desc";

export default function DataTable<T>({
  columns,
  data,
  rowKey,
  emptyMessage = "Sin datos",
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return data;
    const fn = col.sortValue;
    const dir = sortDir === "asc" ? 1 : -1;
    return [...data].sort((a, b) => {
      const va = fn(a);
      const vb = fn(b);
      if (typeof va === "number" && typeof vb === "number") {
        return (va - vb) * dir;
      }
      return String(va).localeCompare(String(vb)) * dir;
    });
  }, [data, columns, sortKey, sortDir]);

  const alignClass = (align?: "left" | "center" | "right") => {
    if (align === "right") return "text-right";
    if (align === "center") return "text-center";
    return "text-left";
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200 bg-neutral-50">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-2 text-xs font-semibold text-neutral-600 ${alignClass(col.align)} ${
                  col.sortValue ? "cursor-pointer select-none hover:text-neutral-900" : ""
                }`}
                onClick={() => col.sortValue && handleSort(col.key)}
              >
                {col.header}
                {sortKey === col.key && (
                  <span className="ml-1">
                    {sortDir === "asc" ? "\u25B2" : "\u25BC"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-3 py-8 text-center text-neutral-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sorted.map((row) => (
              <tr
                key={rowKey(row)}
                className="border-b border-neutral-100 transition-colors hover:bg-neutral-50"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-3 py-2 ${alignClass(col.align)}`}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
