import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastHistory } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

interface HistoryPoint {
  timestamp: number;
  dateLabel: string;
  [candidateName: string]: string | number;
}

function formatTick(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function HistoryTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const ts = payload[0]?.payload?.timestamp;
  return (
    <div
      className="rounded-md border p-2 text-sm shadow-sm"
      style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="mb-1 font-medium" style={{ color: "var(--text-secondary)" }}>
        {ts ? new Date(ts).toLocaleString() : ""}
      </div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span className="inline-block h-[2px] w-3" style={{ backgroundColor: entry.color }} />
          <span style={{ color: "var(--text-muted)" }}>{entry.dataKey}</span>
          <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
            {typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}%
          </span>
        </div>
      ))}
    </div>
  );
}

export function ForecastHistoryChart({ history }: { history: ForecastHistory }) {
  const { snapshots, actuals, election_date } = history;

  if (snapshots.length === 0) {
    return <p style={{ color: "var(--text-muted)" }}>No forecast history yet.</p>;
  }

  const candidateNames = Array.from(
    new Set(snapshots.flatMap((s) => s.results.map((r) => r.candidate.name)))
  );
  const candidateByName = new Map(
    snapshots[0].results.map((r) => [r.candidate.name, r.candidate])
  );

  const data: HistoryPoint[] = snapshots.map((s) => {
    const ts = new Date(s.created_at).getTime();
    const point: HistoryPoint = { timestamp: ts, dateLabel: formatTick(ts) };
    for (const r of s.results) {
      point[r.candidate.name] = r.mean_vote_share;
    }
    return point;
  });

  const electionTs = new Date(election_date + "T00:00:00").getTime();
  const minTs = Math.min(...data.map((d) => d.timestamp));
  const hasActuals = actuals.length > 0;

  const actualPoints = actuals.map((a) => ({
    timestamp: electionTs,
    name: a.candidate.name,
    value: a.vote_pct,
    party: a.candidate.party,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="timestamp"
            type="number"
            domain={[minTs, electionTs]}
            tickFormatter={formatTick}
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "var(--gridline)" }}
          />
          <YAxis
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            domain={[0, 70]}
            tickFormatter={(v) => `${v}%`}
            width={40}
          />
          <Tooltip content={<HistoryTooltip />} />
          <Legend wrapperStyle={{ fontSize: 13, color: "var(--text-secondary)" }} iconType="line" iconSize={16} />
          <ReferenceLine
            x={electionTs}
            stroke="var(--text-muted)"
            strokeDasharray="4 4"
            label={{ value: "Election Day", position: "insideTopRight", fill: "var(--text-muted)", fontSize: 11 }}
          />
          {candidateNames.map((name) => (
            <Line
              key={name}
              data={data}
              type="monotone"
              dataKey={name}
              stroke={partyColorVar(candidateByName.get(name)?.party ?? "")}
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }}
              isAnimationActive={false}
            />
          ))}
          {hasActuals && (
            <Scatter
              name="Actual result"
              data={actualPoints.map((p) => ({ timestamp: p.timestamp, value: p.value }))}
              dataKey="value"
              shape="diamond"
              fill="var(--text-primary)"
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {hasActuals ? (
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          Diamond markers at Election Day show the certified actual result.
        </p>
      ) : (
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          The actual result will appear on this chart after the{" "}
          {new Date(election_date + "T00:00:00").toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}{" "}
          election.
        </p>
      )}
    </div>
  );
}
