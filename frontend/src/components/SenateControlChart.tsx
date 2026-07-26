import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ChamberControl } from "../api/types";
import { partyColorVar } from "../lib/partyColor";
import { UsMap } from "./UsMap";

// Each dot represents a fixed number of simulations rather than one dot per
// raw draw (10,000 of them would be unreadable and tank render performance).
const SIMULATIONS_PER_DOT = 100;
const TOOLTIP_OFFSET = 16;

interface SenateControlChartProps {
  /** state_code -> party currently holding that seat, from the same
   * /races/summary data the main map already loaded -- lets the scenario
   * preview mark a state as a projected flip the same way the main map does. */
  currentHolderByState: Record<string, string>;
}

// UsMap shades a state by win-probability tier (50-60/60-75/75-95/95%+),
// which is exactly the "how dark" mechanism we want for the scenario map --
// just driven by that specific draw's margin instead of a probability. This
// maps margin (points) to a value landing in the tier that reads right for
// that margin size, reusing UsMap's existing tier fills rather than adding
// a second shading system.
function marginToShadeValue(margin: number): number {
  if (margin >= 20) return 0.97;
  if (margin >= 8) return 0.85;
  if (margin >= 3) return 0.68;
  return 0.55;
}

function StatBadge({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1 rounded-md py-3" style={{ backgroundColor: "var(--surface)" }}>
      <span className="text-2xl font-bold tabular-nums" style={{ color }}>
        {(pct * 100).toFixed(0)}%
      </span>
      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
    </div>
  );
}

export function SenateControlChart({ currentHolderByState }: SenateControlChartProps) {
  const [data, setData] = useState<ChamberControl | null>(null);
  // Which specific dot is hovered -- each dot carries its own representative
  // draw (see SIMULATIONS_PER_DOT), not the whole column sharing one example.
  const [hovered, setHovered] = useState<{ columnIndex: number; dotIndex: number } | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, containerWidth: 0, containerHeight: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await api.getSenateControl();
      if (!cancelled) setData(result);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!data) return null;

  const hoveredColumn = hovered ? data.seat_distribution[hovered.columnIndex] : null;
  const hoveredDot = hoveredColumn ? hoveredColumn.dots[hovered!.dotIndex] : null;
  // The dominant_outcome only flips once as dem_seats rises (Republican-
  // majority columns first, then Democratic-majority) -- that boundary is
  // where the majority threshold divider belongs, not a fixed seat number.
  const dividerAfterIndex = data.seat_distribution.findIndex(
    (s, i) => i > 0 && s.dominant_outcome !== data.seat_distribution[i - 1].dominant_outcome
  );

  const scenarioByState: Record<string, { name: string; party: string; margin: number }> = {};
  if (hoveredDot) {
    for (const winner of hoveredDot.example_race_winners) {
      scenarioByState[winner.state_code] = { name: winner.name, party: winner.party, margin: winner.margin };
    }
  }

  const updateMousePos = (e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      containerWidth: rect.width,
      containerHeight: rect.height,
    });
  };
  const anchorRight = mousePos.x > mousePos.containerWidth / 2;
  const popoverStyle: React.CSSProperties = {
    ...(anchorRight
      ? { right: mousePos.containerWidth - mousePos.x + TOOLTIP_OFFSET }
      : { left: mousePos.x + TOOLTIP_OFFSET }),
    bottom: mousePos.containerHeight - mousePos.y + TOOLTIP_OFFSET,
  };

  return (
    <section className="glass-panel mt-6 rounded-lg p-5">
      <div className="mb-1 flex items-start justify-between gap-4">
        <h2 className="font-title text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
          Path to Senate control
        </h2>
        <span className="flex flex-shrink-0 items-center gap-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="relative flex h-3 w-5">
            <span
              className="absolute left-0 h-3 w-3 rounded-full"
              style={{ backgroundColor: "var(--party-democratic)" }}
            />
            <span
              className="absolute left-2 h-3 w-3 rounded-full"
              style={{ backgroundColor: "var(--party-republican)" }}
            />
          </span>
          ~{SIMULATIONS_PER_DOT} simulations per dot
        </span>
      </div>
      <p className="mb-4 text-sm" style={{ color: "var(--text-muted)" }}>
        {data.n_simulations.toLocaleString()} simulated scenarios across all 33 Class 2 races, combined with
        the {data.safe_dem_seats + data.safe_rep_seats} seats not up for election this cycle ({data.safe_dem_seats}{" "}
        safe Dem, {data.safe_rep_seats} safe GOP). Hover a column to preview an example map for that outcome.
      </p>

      <div className="mb-5 flex gap-3">
        <StatBadge label="Dem control" pct={data.dem_win_probability} color="var(--party-democratic)" />
        <StatBadge label="GOP control" pct={data.rep_win_probability} color="var(--party-republican)" />
      </div>

      {/* Popover lives in this outer, non-clipping container -- the dot
          columns get their own scrollable inner wrapper below so a wide
          chart can scroll horizontally without cutting off the popover
          (an element can't be both "overflow-x: auto" and let content
          overflow vertically; the browser forces overflow-y: auto too). */}
      <div ref={containerRef} className="relative" onMouseMove={updateMousePos} onMouseLeave={() => setHovered(null)}>
        <div className="flex items-end justify-center gap-1.5 overflow-x-auto pb-2" style={{ minHeight: 260 }}>
          {data.seat_distribution.map((scenario, i) => {
            const color = partyColorVar(scenario.dominant_outcome);
            const isDivider = i === dividerAfterIndex;
            const isHoveredColumn = hovered?.columnIndex === i;
            // dem_seats is the bucketing key and is fixed for the whole
            // column, but rep_seats can vary dot-to-dot within it (an
            // independent winning a seat shifts rep_seats without changing
            // dem_seats) -- the axis label uses the first dot's value as a
            // representative number for the column, not a column-level field
            // (there isn't one anymore now each dot has its own breakdown).
            const axisLabel =
              scenario.dominant_outcome === "Republican" ? scenario.dots[0]?.rep_seats : scenario.dem_seats;

            return (
              <div
                key={scenario.dem_seats}
                className="flex flex-col items-center gap-1.5"
                style={{
                  borderLeft: isDivider ? "1px dashed var(--border)" : undefined,
                  paddingLeft: isDivider ? 8 : undefined,
                }}
              >
                <div className="flex flex-col-reverse gap-1">
                  {scenario.dots.map((_, d) => {
                    const isHoveredDot = isHoveredColumn && hovered!.dotIndex === d;
                    return (
                      <span
                        key={d}
                        className="block h-3 w-3 cursor-pointer rounded-full"
                        style={{
                          backgroundColor: color,
                          opacity: !hovered || isHoveredDot ? 1 : 0.35,
                        }}
                        onMouseEnter={() => setHovered({ columnIndex: i, dotIndex: d })}
                      />
                    );
                  })}
                </div>
                <span
                  className="text-xs tabular-nums"
                  style={{ color: isHoveredColumn ? "var(--text-primary)" : "var(--text-muted)" }}
                >
                  {axisLabel}
                </span>
              </div>
            );
          })}
        </div>

        {hoveredColumn && hoveredDot && (
          <div
            className="pointer-events-none absolute z-10 w-[400px] rounded-md border p-4 shadow-md"
            style={{ ...popoverStyle, backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
          >
            <p className="mb-2 text-center text-sm" style={{ color: "var(--text-secondary)" }}>
              <span className="font-semibold" style={{ color: partyColorVar("Republican") }}>
                {hoveredDot.rep_seats} GOP
              </span>{" "}
              /{" "}
              <span className="font-semibold" style={{ color: partyColorVar("Democratic") }}>
                {hoveredColumn.dem_seats} DEM
              </span>
              {hoveredDot.independent_seats > 0 && (
                <>
                  {" "}
                  /{" "}
                  <span className="font-semibold" style={{ color: partyColorVar("Independent") }}>
                    {hoveredDot.independent_seats} ind.
                  </span>
                </>
              )}
              <br />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                ~{(hoveredDot.probability * 100).toFixed(2)}% of scenarios · one example combination · darker =
                bigger margin
              </span>
            </p>
            <UsMap
              getVisual={(id) => {
                const winner = scenarioByState[id];
                if (!winner) return null;
                return {
                  party: winner.party,
                  winProbability: marginToShadeValue(winner.margin),
                  isFlip: winner.party !== currentHolderByState[id],
                };
              }}
              isClickable={() => false}
              onStateClick={() => {}}
            />
          </div>
        )}
      </div>
      <p className="mt-1 text-center text-xs" style={{ color: "var(--text-muted)" }}>
        Seats held (out of 100) by whichever party controls that scenario · dashed line marks the majority-control
        boundary
      </p>
    </section>
  );
}
