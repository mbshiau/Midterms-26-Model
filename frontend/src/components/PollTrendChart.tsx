import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Poll } from "../api/types";
import { ChartLegend } from "./ChartLegend";
import { partyColorVar } from "../lib/partyColor";

interface TrendPoint {
  timestamp: number;
  dateLabel: string;
  [candidateName: string]: string | number;
}

function formatTick(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function buildTrendData(polls: Poll[]): { data: TrendPoint[]; candidates: { name: string; party: string }[] } {
  const byName = new Map<string, { name: string; party: string }>();
  const sorted = [...polls].sort(
    (a, b) => new Date(a.field_end_date).getTime() - new Date(b.field_end_date).getTime()
  );

  const data: TrendPoint[] = sorted.map((poll) => {
    const ts = new Date(poll.field_end_date + "T00:00:00").getTime();
    const point: TrendPoint = { timestamp: ts, dateLabel: formatTick(ts) };
    for (const r of poll.results) {
      point[r.candidate.name] = r.pct;
      byName.set(r.candidate.name, { name: r.candidate.name, party: r.candidate.party });
    }
    return point;
  });

  // Winner-first: each candidate's most recent pct (walking newest to
  // oldest, in case they're missing from the very latest poll), so the
  // legend and line-draw order match who's currently ahead in the polls.
  const latestPct = new Map<string, number>();
  for (let i = sorted.length - 1; i >= 0; i--) {
    for (const r of sorted[i].results) {
      if (!latestPct.has(r.candidate.name)) latestPct.set(r.candidate.name, r.pct);
    }
  }
  const candidates = Array.from(byName.values()).sort(
    (a, b) => (latestPct.get(b.name) ?? -1) - (latestPct.get(a.name) ?? -1)
  );

  return { data, candidates };
}

function TrendTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const ts = payload[0]?.payload?.timestamp;
  return (
    <div
      className="rounded-md border p-2 text-sm shadow-sm"
      style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="mb-1 font-medium" style={{ color: "var(--text-secondary)" }}>
        {ts ? new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : ""}
      </div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block h-[2px] w-3"
            style={{ backgroundColor: entry.color }}
          />
          <span style={{ color: "var(--text-muted)" }}>{entry.dataKey}</span>
          <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
            {entry.value}%
          </span>
        </div>
      ))}
    </div>
  );
}

export function PollTrendChart({ polls, electionDate }: { polls: Poll[]; electionDate: string }) {
  const { data, candidates } = buildTrendData(polls);

  if (data.length === 0) {
    return <p style={{ color: "var(--text-muted)" }}>No polls yet.</p>;
  }

  const electionTs = new Date(electionDate + "T00:00:00").getTime();
  const minTs = Math.min(...data.map((d) => d.timestamp));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
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
        <Tooltip content={<TrendTooltip />} />
        <Legend
          content={<ChartLegend items={candidates.map((c) => ({ name: c.name, color: partyColorVar(c.party) }))} />}
        />
        <ReferenceLine
          x={electionTs}
          stroke="var(--text-muted)"
          strokeDasharray="4 4"
          label={{ value: "Election Day", position: "insideTopRight", fill: "var(--text-muted)", fontSize: 11 }}
        />
        {candidates.map((c) => (
          <Line
            key={c.name}
            type="monotone"
            dataKey={c.name}
            stroke={partyColorVar(c.party)}
            strokeWidth={2}
            // A single-poll state has no line segment to draw at all -- fall
            // back to a visible dot so it isn't blank (see the single-poll
            // regression this project hit before), otherwise no dots.
            dot={data.length === 1 ? { r: 4, fill: partyColorVar(c.party), strokeWidth: 2, stroke: "var(--surface)" } : false}
            activeDot={{ r: 5, fill: partyColorVar(c.party), strokeWidth: 2, stroke: "var(--surface)" }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
