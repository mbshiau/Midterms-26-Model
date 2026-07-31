import { useEffect, useState } from "react";
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
import { api } from "../api/client";
import type { ChamberControlHistoryPoint } from "../api/types";
import { ChartLegend } from "./ChartLegend";
import { partyColorVar } from "../lib/partyColor";

interface SeatsPoint {
  timestamp: number;
  Democratic: number;
  Republican: number;
  Independent: number;
}

interface ProbabilityPoint {
  timestamp: number;
  Democratic: number;
  Republican: number;
}

function formatTick(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function SeatsTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const ts = payload[0]?.payload?.timestamp;
  return (
    <div className="rounded-md border p-2 text-sm shadow-sm" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="mb-1 font-medium" style={{ color: "var(--text-secondary)" }}>
        {ts ? new Date(ts).toLocaleDateString() : ""}
      </div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span className="inline-block h-[2px] w-3" style={{ backgroundColor: entry.color }} />
          <span style={{ color: "var(--text-muted)" }}>{entry.dataKey}</span>
          <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
            {typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function ProbabilityTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const ts = payload[0]?.payload?.timestamp;
  // Whichever party is favored that day belongs on top, not a fixed
  // Democratic-then-Republican order (the line/legend order Recharts hands
  // `payload` in matches declaration order, not each day's actual value).
  const sorted = [...payload].sort((a: any, b: any) => b.value - a.value);
  return (
    <div className="rounded-md border p-2 text-sm shadow-sm" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="mb-1 font-medium" style={{ color: "var(--text-secondary)" }}>
        {ts ? new Date(ts).toLocaleDateString() : ""}
      </div>
      {sorted.map((entry: any) => (
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

export function SenateControlHistoryChart() {
  const [points, setPoints] = useState<ChamberControlHistoryPoint[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await api.getSenateControlHistory();
      if (!cancelled) setPoints(result);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!points) return null;

  if (points.length === 0) {
    return (
      <section className="glass-panel mt-6 rounded-lg p-5">
        <h2 className="font-title mb-1 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
          Expected seats & control probability over time
        </h2>
        <p style={{ color: "var(--text-muted)" }}>
          Not enough shared history yet -- this starts accumulating once every modeled race has at least one
          forecast on the same day.
        </p>
      </section>
    );
  }

  const seatsData: SeatsPoint[] = points.map((p) => ({
    timestamp: new Date(p.as_of + "T00:00:00").getTime(),
    Democratic: p.expected_dem_seats,
    Republican: p.expected_rep_seats,
    Independent: p.expected_independent_seats,
  }));
  const probabilityData: ProbabilityPoint[] = points.map((p) => ({
    timestamp: new Date(p.as_of + "T00:00:00").getTime(),
    Democratic: p.dem_win_probability * 100,
    Republican: p.rep_win_probability * 100,
  }));
  const showDots = points.length === 1;

  return (
    <section className="glass-panel mt-6 rounded-lg p-5">
      <h2 className="font-title mb-1 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
        Expected seats & control probability over time
      </h2>
      <p className="mb-4 text-sm" style={{ color: "var(--text-muted)" }}>
        Expected seats is exact (linear -- safe seats plus each race's own win probability). Control probability for
        past days treats every race as independent, since there's no stored historical equivalent of the correlated
        joint simulation above to reconstruct -- it understates real day-to-day uncertainty but shows the genuine
        trend. Today's point uses that same live correlated simulation, so it matches the numbers shown elsewhere on
        this page.
      </p>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-center text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
            Expected seats
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={seatsData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--gridline)" vertical={false} />
              <XAxis
                dataKey="timestamp"
                type="number"
                domain={["dataMin", "dataMax"]}
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
                width={32}
              />
              <Tooltip content={<SeatsTooltip />} />
              <Legend
                content={
                  <ChartLegend
                    items={[
                      { name: "Democratic", color: partyColorVar("Democratic") },
                      { name: "Republican", color: partyColorVar("Republican") },
                      { name: "Independent", color: partyColorVar("Independent") },
                    ]}
                  />
                }
              />
              {(["Democratic", "Republican", "Independent"] as const).map((party) => {
                const color = partyColorVar(party);
                return (
                  <Line
                    key={party}
                    type="monotone"
                    dataKey={party}
                    stroke={color}
                    strokeWidth={2}
                    dot={showDots ? { r: 4, fill: color, strokeWidth: 2, stroke: "var(--surface)" } : false}
                    activeDot={{ r: 5, fill: color, strokeWidth: 2, stroke: "var(--surface)" }}
                    isAnimationActive={false}
                    connectNulls
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h3 className="mb-2 text-center text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
            Probability of Senate control
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={probabilityData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--gridline)" vertical={false} />
              <XAxis
                dataKey="timestamp"
                type="number"
                domain={["dataMin", "dataMax"]}
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
              <Tooltip content={<ProbabilityTooltip />} />
              <Legend
                content={
                  <ChartLegend
                    items={[
                      { name: "Democratic", color: partyColorVar("Democratic") },
                      { name: "Republican", color: partyColorVar("Republican") },
                    ]}
                  />
                }
              />
              {(["Democratic", "Republican"] as const).map((party) => {
                const color = partyColorVar(party);
                return (
                  <Line
                    key={party}
                    type="monotone"
                    dataKey={party}
                    stroke={color}
                    strokeWidth={2}
                    dot={showDots ? { r: 4, fill: color, strokeWidth: 2, stroke: "var(--surface)" } : false}
                    activeDot={{ r: 5, fill: color, strokeWidth: 2, stroke: "var(--surface)" }}
                    isAnimationActive={false}
                    connectNulls
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
