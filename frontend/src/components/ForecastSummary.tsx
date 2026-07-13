import { useState } from "react";
import type { ForecastResult } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

function StatTile({ result }: { result: ForecastResult }) {
  const color = partyColorVar(result.candidate.party);
  const { photo_url, name, incumbent } = result.candidate;
  const [photoFailed, setPhotoFailed] = useState(false);

  return (
    <div
      className="flex-1 rounded-lg border p-4"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
    >
      <div className="flex items-center gap-3">
        {photo_url && !photoFailed ? (
          <img
            src={photo_url}
            alt={name}
            onError={() => setPhotoFailed(true)}
            className="h-10 w-10 flex-shrink-0 rounded-full object-cover"
            style={{ border: `2px solid ${color}` }}
          />
        ) : (
          <span
            className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full"
            style={{ backgroundColor: color }}
          />
        )}
        <span className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          {name}
          {incumbent && <span style={{ color: "var(--text-muted)" }}> (inc.)</span>}
        </span>
      </div>

      <div className="mt-2 text-[40px] font-semibold leading-none tabular-nums" style={{ color: "var(--text-primary)" }}>
        {result.mean_vote_share.toFixed(1)}%
      </div>

      <div className="mt-2 text-sm tabular-nums" style={{ color: "var(--text-muted)" }}>
        95% CI: {result.ci_low.toFixed(1)}%–{result.ci_high.toFixed(1)}%
      </div>
    </div>
  );
}

export function ForecastSummary({ results }: { results: ForecastResult[] }) {
  const sorted = [...results].sort((a, b) => b.mean_vote_share - a.mean_vote_share);
  const margin = sorted.length >= 2 ? sorted[0].mean_vote_share - sorted[1].mean_vote_share : null;

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row">
        {sorted.map((r) => (
          <StatTile key={r.candidate.id} result={r} />
        ))}
      </div>
      {margin !== null && (
        <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
          Projected margin: {sorted[0].candidate.name} +{margin.toFixed(1)} pts
        </p>
      )}
    </div>
  );
}
