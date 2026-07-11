import { useState } from "react";
import usa from "@svg-maps/usa";

interface StateLocation {
  id: string;
  name: string;
  path: string;
}

interface UsMapProps {
  getFill: (stateId: string) => string;
  isClickable: (stateId: string) => boolean;
  onStateClick: (stateId: string) => void;
}

export function UsMap({ getFill, isClickable, onStateClick }: UsMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const locations = usa.locations as StateLocation[];
  const hoveredLocation = locations.find((l) => l.id === hovered);

  return (
    <div className="relative">
      <svg
        viewBox={usa.viewBox}
        role="img"
        aria-label="Map of the United States, click a state to view its forecast"
        className="w-full"
      >
        {locations.map((location) => {
          const clickable = isClickable(location.id);
          return (
            <path
              key={location.id}
              d={location.path}
              fill={getFill(location.id)}
              stroke="var(--surface)"
              strokeWidth={1.5}
              style={{
                cursor: clickable ? "pointer" : "not-allowed",
                opacity: hovered === location.id ? 0.8 : 1,
                transition: "opacity 100ms ease",
              }}
              onMouseEnter={() => setHovered(location.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => clickable && onStateClick(location.id)}
              onFocus={() => setHovered(location.id)}
              onBlur={() => setHovered(null)}
              tabIndex={clickable ? 0 : -1}
              role={clickable ? "button" : undefined}
              aria-label={clickable ? `View ${location.name} forecast` : `${location.name} — no forecast yet`}
              onKeyDown={(e) => {
                if (clickable && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  onStateClick(location.id);
                }
              }}
            />
          );
        })}
      </svg>
      {hoveredLocation && (
        <div
          className="pointer-events-none absolute left-2 top-2 rounded-md border px-2 py-1 text-sm shadow-sm"
          style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          {hoveredLocation.name}
          {!isClickable(hoveredLocation.id) && (
            <span style={{ color: "var(--text-muted)" }}> — coming soon</span>
          )}
        </div>
      )}
    </div>
  );
}
