import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SimulationHistogram } from "../api/types";

function toChartData(hist: SimulationHistogram) {
  return hist.bin_edges.slice(0, -1).map((edge, i) => ({
    binStart: edge,
    binLabel: `${edge.toFixed(0)}–${hist.bin_edges[i + 1].toFixed(0)}%`,
    count: hist.counts[i],
  }));
}

// Isometric skew for the 3D bar's top/side faces: horizontal offset is
// proportional to bar width (wider bars get a proportionally deeper look),
// vertical offset is a fixed small px amount (looking down slightly on the
// top face), matching a classic extruded-column dashboard chart.
const DEPTH_Y = 7;

function partyShades(party: string): { top: string; front: string; frontDark: string; side: string } {
  const slug = party === "Democratic" ? "democratic" : "republican";
  return {
    top: `var(--party-${slug}-50)`,
    front: `var(--party-${slug}-60)`,
    frontDark: `var(--party-${slug}-75)`,
    side: `var(--party-${slug}-95)`,
  };
}

// Recharts' `shape`/`activeBar` render props pass through arbitrary extra
// props we attach on the JSX element (gradientId/glowId/glow below), plus
// its own x/y/width/height for this bar.
function Bar3D(props: any) {
  const { x, y, width, height, gradientId, glowId, glow, party } = props;
  if (height <= 0 || width <= 0) return null;

  const depthX = Math.max(4, width * 0.32);
  const shades = partyShades(party);
  const topPts = [
    `${x},${y}`,
    `${x + depthX},${y - DEPTH_Y}`,
    `${x + width + depthX},${y - DEPTH_Y}`,
    `${x + width},${y}`,
  ].join(" ");
  const sidePts = [
    `${x + width},${y}`,
    `${x + width + depthX},${y - DEPTH_Y}`,
    `${x + width + depthX},${y - DEPTH_Y + height}`,
    `${x + width},${y + height}`,
  ].join(" ");

  return (
    <g filter={glow ? `url(#${glowId})` : undefined} style={{ transition: "filter 150ms ease" }}>
      <polygon points={sidePts} fill={shades.side} />
      <rect x={x} y={y} width={width} height={height} fill={`url(#${gradientId})`} />
      <polygon points={topPts} fill={shades.top} stroke="rgba(255,255,255,0.25)" strokeWidth={0.5} />
    </g>
  );
}

function HistTooltip({ active, payload, color }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div
      className="rounded-md px-3 py-2 text-sm"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        boxShadow: "0 4px 16px rgba(11,11,11,0.15)",
      }}
    >
      <div className="flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        <span style={{ color: "var(--text-muted)" }}>{p.binLabel}</span>
      </div>
      <div className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
        {p.count.toLocaleString()} runs
      </div>
    </div>
  );
}

function SingleHistogram({ hist }: { hist: SimulationHistogram }) {
  const data = toChartData(hist);
  const shades = partyShades(hist.candidate.party);
  const gradientId = `hist-gradient-${hist.candidate.id}`;
  const glowId = `hist-glow-${hist.candidate.id}`;

  return (
    <div
      className="rounded-xl p-5"
      style={{
        background: "rgba(255, 255, 255, 0.6)",
        border: "1px solid rgba(255, 255, 255, 0.7)",
        boxShadow: "0 8px 32px rgba(11, 11, 11, 0.08)",
        backdropFilter: "blur(20px) saturate(160%)",
        WebkitBackdropFilter: "blur(20px) saturate(160%)",
      }}
    >
      <h4 className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
        {hist.candidate.name}
      </h4>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 12, right: 24, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={shades.front} />
              <stop offset="100%" stopColor={shades.frontDark} />
            </linearGradient>
            <filter id={glowId} x="-75%" y="-75%" width="250%" height="250%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="binLabel"
            stroke="var(--gridline)"
            tick={{ fill: "var(--text-muted)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--gridline)" }}
            interval={4}
            padding={{ left: 12, right: 12 }}
          />
          <YAxis hide />
          <Tooltip
            cursor={{ fill: "rgba(11,11,11,0.04)" }}
            content={<HistTooltip color={shades.front} />}
          />
          <Bar
            dataKey="count"
            maxBarSize={30}
            shape={(props: any) => (
              <Bar3D {...props} party={hist.candidate.party} gradientId={gradientId} glowId={glowId} />
            )}
            activeBar={(props: any) => (
              <Bar3D {...props} party={hist.candidate.party} gradientId={gradientId} glowId={glowId} glow />
            )}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SimulationHistograms({ histograms }: { histograms: SimulationHistogram[] }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {histograms.map((h) => (
        <SingleHistogram key={h.candidate.id} hist={h} />
      ))}
    </div>
  );
}
