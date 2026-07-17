import { useRef, useState } from "react";
import usa from "@svg-maps/usa";
import { partyAbbrev, partyColorVar, probabilityTier, type ProbabilityTier } from "../lib/partyColor";

interface StateLocation {
  id: string;
  name: string;
  path: string;
}

export interface MapTooltipCandidate {
  name: string;
  party: string;
  voteShare: number;
}

export interface MapTooltipContent {
  candidates?: MapTooltipCandidate[];
  winner?: { name: string; party: string; probability: number } | null;
}

export interface StateVisual {
  /** Projected winner's party -- drives the fill hue. */
  party: string;
  /** Projected winner's win probability (0-1) -- drives the confidence tier. */
  winProbability: number;
  /** True if the projected winner's party differs from who holds the seat now. */
  isFlip: boolean;
}

interface UsMapProps {
  getVisual: (stateId: string) => StateVisual | null;
  isClickable: (stateId: string) => boolean;
  onStateClick: (stateId: string) => void;
  getTooltip?: (stateId: string) => MapTooltipContent | null;
}

const TOOLTIP_OFFSET = 14;
const PARTY_SLUGS = ["democratic", "republican"] as const;
const TIERS: ProbabilityTier[] = [50, 60, 75, 95];

// The base map's Alaska/Hawaii insets are stock-sized/oriented -- shrink
// Alaska down and enlarge + rotate Hawaii for a more readable inset layout.
// `transformBox: "fill-box"` makes `transform-origin: center` resolve
// against each path's own bounding box, so scale/rotate happen in place
// instead of around the shared SVG viewBox origin.
const LOCATION_TRANSFORMS: Record<string, string> = {
  ak: "scale(0.75)",
  hi: "scale(1.6) rotate(-40deg)",
};

function stripePatternId(slug: string, tier: ProbabilityTier): string {
  return `stripe-${slug}-${tier}`;
}

// A Monte Carlo win probability is never truly 100% -- rounding a
// 99.5%+ result to a flat "100%" overstates the model's own certainty.
function formatWinProbability(probability: number): string {
  const pct = probability * 100;
  return pct >= 99.5 ? ">99%" : `${pct.toFixed(0)}%`;
}

export function UsMap({ getVisual, isClickable, onStateClick, getTooltip }: UsMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, containerWidth: 0, containerHeight: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const locations = usa.locations as StateLocation[];
  const hoveredLocation = locations.find((l) => l.id === hovered);
  const tooltip = hoveredLocation ? getTooltip?.(hoveredLocation.id) ?? null : null;

  const updateMousePos = (e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      containerWidth: rect.width,
      containerHeight: rect.height,
    });
  };

  const anchorRight = mousePos.x > mousePos.containerWidth / 2;
  const anchorBottom = mousePos.y > mousePos.containerHeight / 2;
  const tooltipStyle = {
    ...(anchorRight
      ? { right: mousePos.containerWidth - mousePos.x + TOOLTIP_OFFSET }
      : { left: mousePos.x + TOOLTIP_OFFSET }),
    ...(anchorBottom
      ? { bottom: mousePos.containerHeight - mousePos.y + TOOLTIP_OFFSET }
      : { top: mousePos.y + TOOLTIP_OFFSET }),
  };

  return (
    <div ref={containerRef} className="relative">
      <svg
        viewBox={usa.viewBox}
        role="img"
        aria-label="Map of the United States, click a state to view its forecast"
        className="w-full"
      >
        <defs>
          {PARTY_SLUGS.flatMap((slug) =>
            TIERS.map((tier) => (
              <pattern
                key={stripePatternId(slug, tier)}
                id={stripePatternId(slug, tier)}
                width="8"
                height="8"
                patternTransform="rotate(45)"
                patternUnits="userSpaceOnUse"
              >
                <rect width="8" height="8" fill={`var(--party-${slug}-${tier})`} />
                <line x1="0" y1="0" x2="0" y2="8" stroke="var(--surface)" strokeWidth="3" />
              </pattern>
            ))
          )}
        </defs>
        {locations.map((location) => {
          const clickable = isClickable(location.id);
          const visual = getVisual(location.id);
          const tier = visual ? probabilityTier(visual.party, visual.winProbability) : null;
          const fill =
            tier == null
              ? "var(--gridline)"
              : visual!.isFlip
                ? `url(#${stripePatternId(tier.slug, tier.tier)})`
                : `var(--party-${tier.slug}-${tier.tier})`;

          return (
            <path
              key={location.id}
              d={location.path}
              fill={fill}
              stroke="var(--surface)"
              strokeWidth={1.5}
              style={{
                cursor: clickable ? "pointer" : "not-allowed",
                opacity: hovered === location.id ? 0.8 : 1,
                transition: "opacity 100ms ease",
                ...(LOCATION_TRANSFORMS[location.id]
                  ? {
                      transformBox: "fill-box",
                      transformOrigin: "center",
                      transform: LOCATION_TRANSFORMS[location.id],
                    }
                  : {}),
              }}
              onMouseEnter={(e) => {
                setHovered(location.id);
                updateMousePos(e);
              }}
              onMouseMove={updateMousePos}
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
      {hoveredLocation && tooltip?.candidates && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border px-3 py-2 text-sm shadow-md"
          style={{
            ...tooltipStyle,
            backgroundColor: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            minWidth: "180px",
          }}
        >
          <div className="font-medium">{hoveredLocation.name}</div>
          <div className="mt-1 flex flex-col gap-1">
            {tooltip.candidates.map((c) => (
              <div key={c.name} className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-1.5">
                  <span
                    className="inline-flex h-4 w-4 flex-shrink-0 items-center justify-center text-[9px] font-bold text-white"
                    style={{ backgroundColor: partyColorVar(c.party) }}
                  >
                    {partyAbbrev(c.party)}
                  </span>
                  <span style={{ color: "var(--text-secondary)" }}>{c.name}</span>
                </span>
                <span className="font-semibold tabular-nums">{c.voteShare.toFixed(1)}%</span>
              </div>
            ))}
            {tooltip.winner && (
              <div
                className="mt-1 border-t pt-1 text-xs"
                style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
              >
                <span className="font-semibold" style={{ color: partyColorVar(tooltip.winner.party) }}>
                  {tooltip.winner.name}
                </span>{" "}
                projected to win 

                <span style = {{ color: partyColorVar(tooltip.winner.party) }}>
                &nbsp;({formatWinProbability(tooltip.winner.probability)})
                </span>
              </div>
            )}
            {tooltip.candidates.length >= 2 &&
              (() => {
                const byShareDesc = [...tooltip.candidates].sort((a, b) => b.voteShare - a.voteShare);
                const leader = byShareDesc[0];
                const margin = leader.voteShare - byShareDesc[1].voteShare;
                return (
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Margin:{" "}
                    <span className="font-semibold tabular-nums" style={{ color: partyColorVar(leader.party) }}>
                      {partyAbbrev(leader.party)} +{margin.toFixed(1)}
                    </span>
                  </div>
                );
              })()}
          </div>
        </div>
      )}
    </div>
  );
}
