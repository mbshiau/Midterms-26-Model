import {
  Area,
  CartesianGrid,
  ComposedChart,
  ErrorBar,
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
  [key: string]: string | number | [number, number];
}

function formatTick(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function HistoryTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  const meanEntries = payload.filter((entry: any) => !entry.dataKey.endsWith("Range"));

  return (
    <div
      className="rounded-md border p-2 text-sm shadow-sm"
      style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="mb-1 font-medium" style={{ color: "var(--text-secondary)" }}>
        {point?.timestamp ? new Date(point.timestamp).toLocaleString() : ""}
      </div>
      {meanEntries.map((entry: any) => {
        const range = point?.[`${entry.dataKey}Range`] as [number, number] | undefined;
        return (
          <div key={entry.dataKey} className="flex items-center gap-2">
            <span className="inline-block h-[2px] w-3" style={{ backgroundColor: entry.color }} />
            <span style={{ color: "var(--text-muted)" }}>{entry.dataKey}</span>
            <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
              {typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}%
            </span>
            {range && (
              <span className="tabular-nums" style={{ color: "var(--text-muted)" }}>
                (95% CI: {range[0].toFixed(1)}–{range[1].toFixed(1)}%)
              </span>
            )}
          </div>
        );
      })}
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
      point[`${r.candidate.name}Range`] = [r.ci_low, r.ci_high];
    }
    return point;
  });

  const electionTs = new Date(election_date + "T00:00:00").getTime();
  const minTs = Math.min(...data.map((d) => d.timestamp));
  const hasActuals = actuals.length > 0;
  // A shaded band needs at least 2 points to draw a shape at all -- with
  // exactly 1 snapshot, Recharts can't form a line/area from a single
  // point, so instead show that one point as an explicit dot with a
  // vertical whisker for its 95% CI (via ErrorBar) rather than relying on
  // Recharts' single-point fallback rendering (which ignores dot={false}).
  const hasEnoughForBand = data.length >= 2;

  const actualPoints = actuals.map((a) => ({
    timestamp: electionTs,
    name: a.candidate.name,
    value: a.vote_pct,
    party: a.candidate.party,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
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
            domain={[0, 100]}
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
          {hasEnoughForBand &&
            candidateNames.map((name) => {
              const color = partyColorVar(candidateByName.get(name)?.party ?? "");
              return (
                <Area
                  key={`${name}-band`}
                  type="monotone"
                  dataKey={`${name}Range`}
                  stroke="none"
                  fill={color}
                  fillOpacity={0.15}
                  legendType="none"
                  isAnimationActive={false}
                  dot={false}
                  activeDot={false}
                  connectNulls
                />
              );
            })}
          {hasEnoughForBand &&
            candidateNames.map((name) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={partyColorVar(candidateByName.get(name)?.party ?? "")}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }}
                isAnimationActive={false}
                connectNulls
              />
            ))}
          {!hasEnoughForBand &&
            candidateNames.map((name) => {
              const color = partyColorVar(candidateByName.get(name)?.party ?? "");
              return (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={color}
                  strokeWidth={2}
                  dot={{ r: 5, fill: color, stroke: "var(--surface)", strokeWidth: 2 }}
                  activeDot={{ r: 6, strokeWidth: 2, stroke: "var(--surface)" }}
                  isAnimationActive={false}
                  connectNulls
                >
                  <ErrorBar
                    dataKey={(point: HistoryPoint) => {
                      const range = point[`${name}Range`] as [number, number];
                      const mean = point[name] as number;
                      return [mean - range[0], range[1] - mean];
                    }}
                    width={0}
                    strokeWidth={8}
                    strokeOpacity={0.2}
                    stroke={color}
                    direction="y"
                  />
                </Line>
              );
            })}
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

      <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
        Line shows the projected mean vote share; shaded band is the 95% confidence interval.{" "}
        {hasActuals
          ? "Diamond markers at Election Day show the certified actual result."
          : `The actual result will appear on this chart after the ${new Date(
              election_date + "T00:00:00"
            ).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })} election.`}
      </p>
    </div>
  );
}
