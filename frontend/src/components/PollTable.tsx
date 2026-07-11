import type { Poll } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

function formatDateRange(start: string, end: string): string {
  const fmt = (d: string) =>
    new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return start === end ? fmt(start) : `${fmt(start)}–${fmt(end)}`;
}

export function PollTable({ polls }: { polls: Poll[] }) {
  if (polls.length === 0) {
    return <p style={{ color: "var(--text-muted)" }}>No general-election polls have been published yet.</p>;
  }

  const sorted = [...polls].sort(
    (a, b) => new Date(b.field_end_date).getTime() - new Date(a.field_end_date).getTime()
  );
  const maxWeight = Math.max(...polls.map((p) => p.weight), 1e-9);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left" style={{ borderColor: "var(--border)" }}>
            <th className="py-2 pr-4 font-medium" style={{ color: "var(--text-muted)" }}>
              Pollster
            </th>
            <th className="py-2 pr-4 font-medium" style={{ color: "var(--text-muted)" }}>
              Field dates
            </th>
            <th className="py-2 pr-4 text-right font-medium" style={{ color: "var(--text-muted)" }}>
              Sample
            </th>
            <th className="py-2 pr-4 font-medium" style={{ color: "var(--text-muted)" }}>
              Pop.
            </th>
            <th className="py-2 pr-4 text-left font-medium" style={{ color: "var(--text-muted)" }}>
              Results
            </th>
            <th className="py-2 pr-4 text-right font-medium" style={{ color: "var(--text-muted)" }}>
              Undecided
            </th>
            <th className="py-2 pr-4 text-right font-medium" style={{ color: "var(--text-muted)" }}>
              MoE
            </th>
            <th className="py-2 pr-4 font-medium" style={{ color: "var(--text-muted)" }}>
              Weight
            </th>
            <th className="py-2 font-medium" style={{ color: "var(--text-muted)" }}>
              Source
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((poll) => (
            <tr key={poll.id} className="border-b" style={{ borderColor: "var(--border)" }}>
              <td className="py-2 pr-4" style={{ color: "var(--text-primary)" }}>
                {poll.pollster}
              </td>
              <td className="py-2 pr-4 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                {formatDateRange(poll.field_start_date, poll.field_end_date)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums" style={{ color: "var(--text-secondary)" }}>
                {poll.sample_size.toLocaleString()}
              </td>
              <td className="py-2 pr-4" style={{ color: "var(--text-secondary)" }}>
                {poll.population}
              </td>
              <td className="py-2 pr-4">
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  {poll.results.map((r) => (
                    <span key={r.candidate.id} className="inline-flex items-center gap-1.5">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: partyColorVar(r.candidate.party) }}
                      />
                      <span style={{ color: "var(--text-muted)" }}>{r.candidate.name.split(" ").at(-1)}</span>
                      <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                        {r.pct.toFixed(0)}%
                      </span>
                    </span>
                  ))}
                </div>
              </td>
              <td className="py-2 pr-4 text-right tabular-nums" style={{ color: "var(--text-secondary)" }}>
                {poll.undecided_pct.toFixed(0)}%
              </td>
              <td className="py-2 pr-4 text-right tabular-nums" style={{ color: "var(--text-secondary)" }}>
                {poll.margin_of_error != null ? `±${poll.margin_of_error.toFixed(1)}` : "—"}
              </td>
              <td className="py-2 pr-4">
                <div className="flex items-center gap-2" title={`${(poll.weight * 100).toFixed(1)}% of total polling weight`}>
                  <div className="h-1.5 w-14 overflow-hidden rounded-full" style={{ backgroundColor: "var(--gridline)" }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(poll.weight / maxWeight) * 100}%`,
                        backgroundColor: "var(--party-democratic)",
                      }}
                    />
                  </div>
                  <span className="tabular-nums text-xs" style={{ color: "var(--text-muted)" }}>
                    {(poll.weight * 100).toFixed(1)}%
                  </span>
                </div>
              </td>
              <td className="py-2">
                <a
                  href={poll.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline"
                  style={{ color: "var(--text-muted)" }}
                >
                  link
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
