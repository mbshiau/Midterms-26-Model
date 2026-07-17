import { useState } from "react";
import type { ForecastResult } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

const CX = 170;
const CY = 168;
const OUTER_R = 150;
const INNER_R = 106;
const NEEDLE_LENGTH = 128;
const NEEDLE_BASE_HALF_WIDTH = 7;
const CLIP_ID = "forecast-needle-clip";
const SVG_W = 340;
const SVG_H = 185;

// Left (angle 180°) is fully Democratic, right (angle 0°) is fully
// Republican. SVG has no native angle-based ("conic") gradient, and a plain
// linearGradient varies by x-coordinate -- at a fixed angle, the inner and
// outer edge of the arc sit at different x (unless the angle is exactly
// 90°), so the same point on the dial could read as two different colors
// depending on radius. Fixing that while keeping a smooth blend (rather
// than stepped bands) means reaching for CSS's real conic-gradient, applied
// via a foreignObject clipped to the arc shape -- color there is purely a
// function of angle around the center point, so radius never affects it.
// Stop positions/colors mirror the same 4-tier confidence breakpoints
// (50/60/75/95) used everywhere else in the app (the map, etc), expressed
// in degrees across the 180° arc (0deg = angle 180 = full Democratic,
// 180deg = angle 0 = full Republican).
const GRADIENT_STOPS: { angleDeg: number; color: string }[] = [
  { angleDeg: 4.5, color: "var(--party-democratic-95)" },
  { angleDeg: 27, color: "var(--party-democratic-75)" },
  { angleDeg: 58.5, color: "var(--party-democratic-60)" },
  { angleDeg: 81, color: "var(--party-democratic-50)" },
  { angleDeg: 99, color: "var(--party-republican-50)" },
  { angleDeg: 121.5, color: "var(--party-republican-60)" },
  { angleDeg: 153, color: "var(--party-republican-75)" },
  { angleDeg: 175.5, color: "var(--party-republican-95)" },
];

function polarPoint(radius: number, angleDeg: number): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: CX + radius * Math.cos(rad), y: CY - radius * Math.sin(rad) };
}

function bandPath(innerR: number, outerR: number, a0: number, a1: number): string {
  const outer0 = polarPoint(outerR, a0);
  const outer1 = polarPoint(outerR, a1);
  const inner1 = polarPoint(innerR, a1);
  const inner0 = polarPoint(innerR, a0);
  return [
    `M ${outer0.x} ${outer0.y}`,
    `A ${outerR} ${outerR} 0 0 0 ${outer1.x} ${outer1.y}`,
    `L ${inner1.x} ${inner1.y}`,
    `A ${innerR} ${innerR} 0 0 1 ${inner0.x} ${inner0.y}`,
    "Z",
  ].join(" ");
}

function formatPct(p: number): string {
  if (p >= 0.999) return ">99%";
  if (p <= 0.001) return "<1%";
  return `${(p * 100).toFixed(1)}%`;
}

function CandidateLabel({
  result,
  align,
}: {
  result: ForecastResult;
  align: "left" | "right";
}) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const { photo_url, name, incumbent } = result.candidate;
  const color = partyColorVar(result.candidate.party);

  return (
    <div className={`flex items-center gap-2.5 ${align === "right" ? "flex-row-reverse text-right" : ""}`}>
      {photo_url && !photoFailed ? (
        <img
          src={photo_url}
          alt={name}
          onError={() => setPhotoFailed(true)}
          className="h-9 w-9 flex-shrink-0 rounded-full object-cover"
          style={{ border: `2px solid ${color}` }}
        />
      ) : (
        <span
          className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
      )}
      <div>
        <div className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          {name}
          {incumbent && <span style={{ color: "var(--text-muted)" }}> (inc.)</span>}
        </div>
        <div className="text-2xl font-semibold leading-tight" style={{ color: "var(--text-primary)" }}>
          {result.mean_vote_share.toFixed(1)}%
        </div>
        <div className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
          {result.ci_low.toFixed(1)}–{result.ci_high.toFixed(1)}%
        </div>
      </div>
    </div>
  );
}

export function ForecastNeedle({ results }: { results: ForecastResult[] }) {
  const sorted = [...results].sort((a, b) => b.mean_vote_share - a.mean_vote_share);
  const dem = results.find((r) => r.candidate.party === "Democratic") ?? sorted[1] ?? sorted[0];
  const rep = results.find((r) => r.candidate.party === "Republican") ?? sorted[0];
  const leader = sorted[0];
  const margin = sorted.length >= 2 ? sorted[0].mean_vote_share - sorted[1].mean_vote_share : null;

  // pDem: how far toward the Democratic candidate the needle points (0 = fully
  // Republican / right, 1 = fully Democratic / left, 0.5 = toss-up / straight up).
  const pDem = dem.win_probability;
  const needleAngle = pDem * 180;
  const needleTip = polarPoint(NEEDLE_LENGTH, needleAngle);
  const needleLeftBase = polarPoint(NEEDLE_BASE_HALF_WIDTH, needleAngle + 90);
  const needleRightBase = polarPoint(NEEDLE_BASE_HALF_WIDTH, needleAngle - 90);

  // CSS conic-gradient() angles start at 12 o'clock and increase clockwise,
  // whereas our polarPoint() angles start at 3 o'clock and increase
  // counter-clockwise -- "from 270deg" rotates the gradient's own 0deg mark
  // to 9 o'clock (our angle 180, full Democratic), so walking the stops
  // from 0deg to 180deg sweeps left -> top -> right, matching angle 180 -> 0.
  const conicGradient = `conic-gradient(from 270deg at ${CX}px ${CY}px, ${GRADIENT_STOPS.map(
    (s) => `${s.color} ${s.angleDeg}deg`
  ).join(", ")})`;

  return (
    <div>
      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full" style={{ maxHeight: 210 }} role="img" aria-label="Forecast needle">
        <defs>
          <clipPath id={CLIP_ID}>
            <path d={bandPath(INNER_R, OUTER_R, 0, 180)} />
          </clipPath>
        </defs>
        <foreignObject x={0} y={0} width={SVG_W} height={SVG_H} clipPath={`url(#${CLIP_ID})`}>
          <div
            // @ts-expect-error -- xmlns is required on foreignObject content but isn't in React's HTML div typings
            xmlns="http://www.w3.org/1999/xhtml"
            style={{ width: `${SVG_W}px`, height: `${SVG_H}px`, background: conicGradient }}
          />
        </foreignObject>
        <polygon
          points={`${needleTip.x},${needleTip.y} ${needleLeftBase.x},${needleLeftBase.y} ${needleRightBase.x},${needleRightBase.y}`}
          fill="var(--text-primary)"
        />
        <circle cx={CX} cy={CY} r={9} fill="var(--text-primary)" stroke="var(--surface)" strokeWidth={2} />
      </svg>

      <p className="-mt-2 text-center text-sm" style={{ color: "var(--text-muted)" }}>
        <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
          {leader.candidate.name}
        </span>{" "}
        favored, {formatPct(leader.win_probability)}
      </p>

      <div className="mt-4 flex items-start justify-between gap-4">
        <CandidateLabel result={dem} align="left" />
        <CandidateLabel result={rep} align="right" />
      </div>

      {margin !== null && (
        <p className="mt-3 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Projected margin: {sorted[0].candidate.name} +{margin.toFixed(1)} pts
        </p>
      )}
    </div>
  );
}
