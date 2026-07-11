import type { ForecastSnapshot } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

function signed(n: number, digits = 1): string {
  const sign = n > 0 ? "+" : n < 0 ? "−" : "±";
  return `${sign}${Math.abs(n).toFixed(digits)}`;
}

const OTHER_FUNDAMENTALS_ROWS: { key: keyof ForecastSnapshot["fundamentals_breakdown"]; label: string }[] = [
  { key: "incumbency_pts", label: "Incumbency" },
  { key: "registration_trend_pts", label: "Voter registration trend" },
  { key: "national_environment_pts", label: "National environment (presidential approval)" },
];

export function ModelCompositionCard({
  forecast,
  stateName,
}: {
  forecast: ForecastSnapshot;
  stateName: string;
}) {
  const pollPct = forecast.poll_weight_alpha * 100;
  const fundamentalsPct = 100 - pollPct;
  const sorted = [...forecast.results].sort((a, b) => b.mean_vote_share - a.mean_vote_share);
  const historicalLeanRows: { key: keyof ForecastSnapshot["fundamentals_breakdown"]; label: string }[] = [
    { key: "gubernatorial_lean_pts", label: `${stateName} gubernatorial lean (last 3 races, recency-weighted)` },
    { key: "senate_lean_pts", label: `${stateName} Senate lean (last 3 races, recency-weighted)` },
    { key: "presidential_lean_pts", label: `${stateName} presidential lean (last 3 races, recency-weighted)` },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
          Polls vs. fundamentals weight
        </h3>
        <div className="mt-3 flex h-4 w-full gap-[2px]" role="img" aria-label="Polls vs fundamentals weight">
          <div
            className="h-full rounded-l-[4px]"
            style={{ width: `${pollPct}%`, backgroundColor: "var(--party-democratic)" }}
            title={`Polling: ${pollPct.toFixed(0)}%`}
          />
          <div
            className="h-full rounded-r-[4px]"
            style={{ width: `${fundamentalsPct}%`, backgroundColor: "var(--text-muted)" }}
            title={`Fundamentals: ${fundamentalsPct.toFixed(0)}%`}
          />
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          {pollPct.toFixed(0)}% polling · {fundamentalsPct.toFixed(0)}% fundamentals — shifts toward
          100% polling as Election Day approaches.
        </p>
      </div>

      <div className="overflow-x-auto">
        <h3 className="mb-2 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
          Per-candidate composition
        </h3>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left" style={{ borderColor: "var(--border)" }}>
              <th className="py-1.5 pr-4 font-medium" style={{ color: "var(--text-muted)" }}>
                Candidate
              </th>
              <th className="py-1.5 pr-4 text-right font-medium" style={{ color: "var(--text-muted)" }}>
                Polling-only
              </th>
              <th className="py-1.5 pr-4 text-right font-medium" style={{ color: "var(--text-muted)" }}>
                Fundamentals-only
              </th>
              <th className="py-1.5 text-right font-medium" style={{ color: "var(--text-muted)" }}>
                Blended forecast
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.candidate.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                <td className="py-1.5 pr-4">
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: partyColorVar(r.candidate.party) }}
                    />
                    <span style={{ color: "var(--text-primary)" }}>{r.candidate.name}</span>
                  </span>
                </td>
                <td className="py-1.5 pr-4 text-right tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  {r.polling_vote_share.toFixed(1)}%
                </td>
                <td className="py-1.5 pr-4 text-right tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  {r.fundamentals_vote_share.toFixed(1)}%
                </td>
                <td className="py-1.5 text-right font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {r.mean_vote_share.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
          Fundamentals inputs (Democratic margin, points)
        </h3>
        <ul className="flex flex-col gap-1.5 text-sm">
          {historicalLeanRows.map((row) => (
            <li key={row.key} className="flex items-center justify-between">
              <span style={{ color: "var(--text-secondary)" }}>{row.label}</span>
              <span className="tabular-nums font-medium" style={{ color: "var(--text-primary)" }}>
                {signed(forecast.fundamentals_breakdown[row.key] as number)}
              </span>
            </li>
          ))}
          <li className="flex items-center justify-between">
            <span style={{ color: "var(--text-secondary)" }}>
              Combined historical lean (45% gov. / 30% Senate / 25% pres.)
            </span>
            <span className="tabular-nums font-medium" style={{ color: "var(--text-primary)" }}>
              {signed(forecast.fundamentals_breakdown.combined_historical_lean_pts)}
            </span>
          </li>
          {OTHER_FUNDAMENTALS_ROWS.map((row) => (
            <li key={row.key} className="flex items-center justify-between">
              <span style={{ color: "var(--text-secondary)" }}>{row.label}</span>
              <span className="tabular-nums font-medium" style={{ color: "var(--text-primary)" }}>
                {signed(forecast.fundamentals_breakdown[row.key] as number)}
              </span>
            </li>
          ))}
          <li
            className="flex items-center justify-between border-t pt-1.5"
            style={{ borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--text-secondary)" }}>Combined fundamentals margin</span>
            <span className="tabular-nums font-semibold" style={{ color: "var(--text-primary)" }}>
              {signed(forecast.fundamentals_breakdown.total_dem_margin_pts)}
            </span>
          </li>
        </ul>
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          National environment uses {forecast.fundamentals_breakdown.president_name}&rsquo;s{" "}
          {forecast.fundamentals_breakdown.president_approval_pct.toFixed(1)}% approval rating as of{" "}
          {new Date(forecast.fundamentals_breakdown.president_approval_as_of + "T00:00:00").toLocaleDateString(
            "en-US",
            { month: "short", day: "numeric", year: "numeric" }
          )}{" "}
          (
          <a
            href={forecast.fundamentals_breakdown.president_approval_source_url}
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            source
          </a>
          ).
        </p>
      </div>
    </div>
  );
}
