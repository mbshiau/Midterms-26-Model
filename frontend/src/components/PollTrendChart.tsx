import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Poll } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

interface TrendPoint {
  date: string;
  dateLabel: string;
  [candidateName: string]: string | number;
}

function buildTrendData(polls: Poll[]): { data: TrendPoint[]; candidates: { name: string; party: string }[] } {
  const byName = new Map<string, { name: string; party: string }>();
  const sorted = [...polls].sort(
    (a, b) => new Date(a.field_end_date).getTime() - new Date(b.field_end_date).getTime()
  );

  const data: TrendPoint[] = sorted.map((poll) => {
    const point: TrendPoint = {
      date: poll.field_end_date,
      dateLabel: new Date(poll.field_end_date + "T00:00:00").toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
    };
    for (const r of poll.results) {
      point[r.candidate.name] = r.pct;
      byName.set(r.candidate.name, { name: r.candidate.name, party: r.candidate.party });
    }
    return point;
  });

  return { data, candidates: Array.from(byName.values()) };
}

function TrendTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-md border p-2 text-sm shadow-sm"
      style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="mb-1 font-medium" style={{ color: "var(--text-secondary)" }}>
        {label}
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

export function PollTrendChart({ polls }: { polls: Poll[] }) {
  const { data, candidates } = buildTrendData(polls);

  if (data.length === 0) {
    return <p style={{ color: "var(--text-muted)" }}>No polls yet.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="dateLabel"
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
          wrapperStyle={{ fontSize: 13, color: "var(--text-secondary)" }}
          iconType="line"
          iconSize={16}
        />
        {candidates.map((c) => (
          <Line
            key={c.name}
            type="monotone"
            dataKey={c.name}
            stroke={partyColorVar(c.party)}
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
