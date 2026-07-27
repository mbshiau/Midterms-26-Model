import type { CSSProperties, ReactNode } from "react";

interface OrbProps {
  value: string;
  color: string;
  size?: "lg" | "md" | "sm";
  floatDelay?: number;
  className?: string;
  children: ReactNode;
}

// Diameter + the value/sublabel font sizes that read well at that diameter --
// keyed together so a bigger orb doesn't end up with cramped or oversized text.
const SIZE_PX: Record<NonNullable<OrbProps["size"]>, { diameter: number; value: number; label: number }> = {
  lg: { diameter: 232, value: 56, label: 15 },
  md: { diameter: 184, value: 40, label: 13.5 },
  sm: { diameter: 156, value: 32, label: 12.5 },
};

/** A translucent, backlit sphere -- the "orb" stand-in for the reference
 * layout's hexagons. Color comes in entirely via --orb-color (see
 * .orb-glass in index.css) so this stays a plain shape + two text lines. */
export function Orb({ value, color, size = "md", floatDelay = 0, className, children }: OrbProps) {
  const { diameter, value: valuePx, label: labelPx } = SIZE_PX[size];

  return (
    <div
      className={`orb-glass orb-float flex flex-shrink-0 flex-col items-center justify-center rounded-full text-center ${className ?? ""}`}
      style={
        {
          "--orb-color": color,
          width: diameter,
          height: diameter,
          animationDelay: `${floatDelay}s`,
          padding: diameter * 0.14,
        } as CSSProperties
      }
    >
      <span className="font-title font-semibold tabular-nums" style={{ color, fontSize: valuePx, lineHeight: 1 }}>
        {value}
      </span>
      <span className="mt-1.5" style={{ fontSize: labelPx, lineHeight: 1.25, color: "var(--text-secondary)" }}>
        {children}
      </span>
    </div>
  );
}
