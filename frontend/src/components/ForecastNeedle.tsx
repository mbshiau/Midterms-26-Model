import { useState } from "react";
import type { ForecastResult } from "../api/types";
import { partyColorVar, probabilityColorVar } from "../lib/partyColor";

const CX = 170;
const CY = 168;
const OUTER_R = 150;
const INNER_R = 106;
const NEEDLE_LENGTH = 128;
const NEEDLE_BASE_HALF_WIDTH = 7;

// Same 4-tier confidence breakpoints as probabilityTier (50/60/75/95),
// mirrored across the toss-up center so the arc's color reads identically
// to every other win-probability encoding in the app (the map, etc).
const BAND_BOUNDARIES = [0, 0.05, 0.25, 0.4, 0.5, 0.6, 0.75, 0.95, 1];

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

/** pDemocratic in [0,1] -- the fraction of the arc's span (right=Republican,
 * left=Democratic) this band sits at. Returns the same tiered color the rest
 * of the app uses for a win probability of that magnitude. */
function bandColor(pDemMidpoint: number): string {
  const party = pDemMidpoint < 0.5 ? "Republican" : "Democratic";
  const winProbability = party === "Republican" ? 1 - pDemMidpoint : pDemMidpoint;
  return probabilityColorVar(party, winProbability);
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

  return (
    <div>
      <svg viewBox="0 0 340 185" className="w-full" style={{ maxHeight: 210 }} role="img" aria-label="Forecast needle">
        {BAND_BOUNDARIES.slice(0, -1).map((a0Frac, i) => {
          const a1Frac = BAND_BOUNDARIES[i + 1];
          const mid = (a0Frac + a1Frac) / 2;
          return (
            <path
              key={i}
              d={bandPath(INNER_R, OUTER_R, a0Frac * 180, a1Frac * 180)}
              fill={bandColor(mid)}
            />
          );
        })}
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
