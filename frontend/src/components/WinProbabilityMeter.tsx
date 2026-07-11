import type { ForecastResult } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

function formatPct(p: number): string {
  if (p >= 0.999) return ">99%";
  if (p <= 0.001) return "<1%";
  return `${(p * 100).toFixed(1)}%`;
}

export function WinProbabilityMeter({ results }: { results: ForecastResult[] }) {
  const sorted = [...results].sort((a, b) => b.win_probability - a.win_probability);

  return (
    <div>
      <h3 className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Win probability
      </h3>

      <div className="mt-3 flex h-6 w-full gap-[2px]" role="img" aria-label="Win probability by candidate">
        {sorted.map((r) => (
          <div
            key={r.candidate.id}
            className="h-full first:rounded-l-[4px] last:rounded-r-[4px]"
            style={{
              width: `${Math.max(r.win_probability * 100, 0.5)}%`,
              backgroundColor: partyColorVar(r.candidate.party),
            }}
            title={`${r.candidate.name}: ${formatPct(r.win_probability)}`}
          />
        ))}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
        {sorted.map((r) => (
          <div key={r.candidate.id} className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: partyColorVar(r.candidate.party) }}
            />
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {r.candidate.name}
            </span>
            <span
              className="text-sm font-semibold tabular-nums"
              style={{ color: "var(--text-primary)" }}
            >
              {formatPct(r.win_probability)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
