import { useRef, useState } from "react";
import { ALL_DISTRICT_PATHS, MAP_VIEWBOX } from "../data/allDistrictShapes";
import type { MapTooltipCandidate } from "./UsMap";
import { partyAbbrev, partyColorVar, probabilityTier, type ProbabilityTier } from "../lib/partyColor";

export interface HouseDistrictVisual {
  party: string;
  winProbability: number;
  /** True if the projected winner's party differs from who holds the seat
   * now -- rendered as a diagonal-stripe fill instead of a solid one, same
   * convention as UsMap's projected-flip indicator. */
  isFlip: boolean;
}

const PARTY_SLUGS = ["democratic", "republican", "independent"] as const;
const TIERS: ProbabilityTier[] = [50, 60, 75, 95];

function stripePatternId(slug: string, tier: ProbabilityTier): string {
  return `district-stripe-${slug}-${tier}`;
}

export interface HouseTooltipContent {
  title: string;
  candidates?: MapTooltipCandidate[];
  winner?: { name: string; party: string; probability: number } | null;
}

interface HouseDistrictMapProps {
  /** Race.slug -> visual, e.g. { "al-house-01": { party: "Democratic", winProbability: 0.7 } }.
   * All 435 current districts have a path in ALL_DISTRICT_PATHS (see
   * data/allDistrictShapes.ts) -- a slug missing from `visualsBySlug` (no
   * forecast data yet) is still drawn, just in the neutral "no data" fill
   * and not clickable, rather than left out of the map entirely. */
  visualsBySlug: Record<string, HouseDistrictVisual>;
  onDistrictClick: (slug: string) => void;
  getTooltip?: (slug: string) => HouseTooltipContent | null;
}

const TOOLTIP_OFFSET = 14;

// A Monte Carlo win probability is never truly 100% -- rounding a 99.5%+
// result to a flat "100%" overstates the model's own certainty. Same
// convention as UsMap's formatWinProbability.
function formatWinProbability(probability: number): string {
  const pct = probability * 100;
  return pct >= 99.5 ? ">99%" : `${pct.toFixed(0)}%`;
}

export function HouseDistrictMap({ visualsBySlug, onDistrictClick, getTooltip }: HouseDistrictMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, containerWidth: 0, containerHeight: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltip = hovered ? getTooltip?.(hovered) ?? null : null;

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
      <svg viewBox={MAP_VIEWBOX} role="img" aria-label="Map of U.S. congressional districts" className="w-full">
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
        {Object.entries(ALL_DISTRICT_PATHS).map(([slug, path]) => {
          const visual = visualsBySlug[slug];
          const tier = visual ? probabilityTier(visual.party, visual.winProbability) : null;
          const fill =
            tier == null
              ? "var(--gridline)"
              : visual!.isFlip
                ? `url(#${stripePatternId(tier.slug, tier.tier)})`
                : `var(--party-${tier.slug}-${tier.tier})`;
          const clickable = Boolean(visual);

          return (
            <path
              key={slug}
              d={path.d}
              transform={path.transform}
              fill={fill}
              stroke="var(--surface)"
              strokeWidth={0.6}
              style={{
                cursor: clickable ? "pointer" : "default",
                opacity: hovered === slug ? 0.8 : 1,
                transition: "opacity 100ms ease",
              }}
              onMouseEnter={(e) => {
                setHovered(slug);
                updateMousePos(e);
              }}
              onMouseMove={updateMousePos}
              onMouseLeave={() => setHovered(null)}
              onClick={() => clickable && onDistrictClick(slug)}
            />
          );
        })}
      </svg>
      {tooltip && (
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
          <div className="font-medium">{tooltip.title}</div>
          {tooltip.candidates && tooltip.candidates.length > 0 ? (
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
                  projected to win{" "}
                  <span style={{ color: partyColorVar(tooltip.winner.party) }}>
                    ({formatWinProbability(tooltip.winner.probability)})
                  </span>
                </div>
              )}
              {tooltip.candidates.length >= 2 &&
                (() => {
                  const byShareDesc = [...tooltip.candidates!].sort((a, b) => b.voteShare - a.voteShare);
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
          ) : (
            <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              No forecast yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
