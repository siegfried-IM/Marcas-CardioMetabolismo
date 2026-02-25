interface PillItem {
  id: string;
  label: string;
  color: string;
}

interface PillSelectorProps {
  items: PillItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

export default function PillSelector({
  items,
  activeId,
  onSelect,
}: PillSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        const isActive = item.id === activeId;
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className="flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all"
            style={{
              borderColor: isActive ? item.color : "#d4d4d8",
              backgroundColor: isActive ? item.color : "transparent",
              color: isActive ? "#fff" : "#52525b",
            }}
          >
            {/* Color dot (visible when not active) */}
            {!isActive && (
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: item.color }}
              />
            )}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
