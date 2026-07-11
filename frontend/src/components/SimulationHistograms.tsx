import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SimulationHistogram } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

function toChartData(hist: SimulationHistogram) {
  return hist.bin_edges.slice(0, -1).map((edge, i) => ({
    binStart: edge,
    binLabel: `${edge.toFixed(0)}–${hist.bin_edges[i + 1].toFixed(0)}%`,
    count: hist.counts[i],
  }));
}

function HistTooltip({ active, payload, color }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div
      className="rounded-md border p-2 text-sm shadow-sm"
      style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="flex items-center gap-2">
        <span className="inline-block h-[2px] w-3" style={{ backgroundColor: color }} />
        <span style={{ color: "var(--text-muted)" }}>{p.binLabel}</span>
      </div>
      <div className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
        {p.count.toLocaleString()} runs
      </div>
    </div>
  );
}

function SingleHistogram({ hist }: { hist: SimulationHistogram }) {
  const color = partyColorVar(hist.candidate.party);
  const data = toChartData(hist);

  return (
    <div>
      <h4 className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
        {hist.candidate.name}
      </h4>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 16 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="binLabel"
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--gridline)" }}
            interval={4}
            padding={{ left: 12, right: 12 }}
          />
          <YAxis hide />
          <Tooltip content={<HistTooltip color={color} />} />
          <Bar dataKey="count" fill={color} radius={[4, 4, 0, 0]} maxBarSize={10} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SimulationHistograms({ histograms }: { histograms: SimulationHistogram[] }) {
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
      {histograms.map((h) => (
        <SingleHistogram key={h.candidate.id} hist={h} />
      ))}
    </div>
  );
}
