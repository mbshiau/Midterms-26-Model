import { useMemo, useRef, useState } from "react";
import type { MapTooltipCandidate } from "./UsMap";
import { partyAbbrev, partyColorVar, probabilityTier, type ProbabilityTier } from "../lib/partyColor";

export interface HouseDistrictVisual {
  party: string;
  winProbability: number;
  /** True if the projected winner's party differs from who holds the seat
   * now -- rendered as a diagonal-stripe fill instead of a solid one, same
   * convention as UsMap's projected-flip indicator. */
  isFlip: boolean;
}

export interface HouseTooltipContent {
  title: string;
  candidates?: MapTooltipCandidate[];
  winner?: { name: string; party: string; probability: number } | null;
}

export interface HouseDistrictRef {
  slug: string;
  stateCode: string;
}

interface HouseDistrictMapProps {
  /** Every current House race (slug + state), independent of whether a
   * forecast exists yet -- drives which hexagons get drawn at all. A slug
   * missing from `visualsBySlug` is still drawn, just in the neutral
   * "no data" fill and not clickable, rather than left out of the map. */
  districts: HouseDistrictRef[];
  /** Race.slug -> visual, e.g. { "al-house-01": { party: "Democratic", winProbability: 0.7 } }. */
  visualsBySlug: Record<string, HouseDistrictVisual>;
  onDistrictClick: (slug: string) => void;
  getTooltip?: (slug: string) => HouseTooltipContent | null;
}

const PARTY_SLUGS = ["democratic", "republican", "independent"] as const;
const TIERS: ProbabilityTier[] = [50, 60, 75, 95];

function stripePatternId(slug: string, tier: ProbabilityTier): string {
  return `district-stripe-${slug}-${tier}`;
}

const TOOLTIP_OFFSET = 14;

// A Monte Carlo win probability is never truly 100% -- rounding a 99.5%+
// result to a flat "100%" overstates the model's own certainty. Same
// convention as UsMap's formatWinProbability.
function formatWinProbability(probability: number): string {
  const pct = probability * 100;
  return pct >= 99.5 ? ">99%" : `${pct.toFixed(0)}%`;
}

function districtNumber(slug: string): number {
  const parts = slug.split("-");
  return Number(parts[parts.length - 1]);
}

// Rough tile-grid position of each state, laid out to read as the outline of
// the continental US (plus AK/HI pulled in as insets, bottom-left) -- not a
// literal geographic projection, just an ordinally-correct west->east,
// north->south placement with enough room between neighbors for even the
// biggest states' hex clusters (CA/TX at 50+ districts) not to collide.
const STATE_GRID_POSITION: Record<string, { col: number; row: number }> = {
  ak: { col: 0, row: 7 },
  hi: { col: 1, row: 7 },

  wa: { col: 1, row: 0 },
  or: { col: 1, row: 1 },
  ca: { col: 1, row: 2 },

  id: { col: 2, row: 1 },
  nv: { col: 2, row: 2 },
  az: { col: 2, row: 3 },

  mt: { col: 3, row: 0 },
  wy: { col: 3, row: 1 },
  ut: { col: 3, row: 2 },
  nm: { col: 3, row: 3 },

  nd: { col: 4, row: 0 },
  sd: { col: 4, row: 1 },
  co: { col: 4, row: 2 },
  ks: { col: 4, row: 3 },
  ok: { col: 4, row: 4 },
  tx: { col: 4, row: 5 },

  mn: { col: 5, row: 0 },
  ia: { col: 5, row: 1 },
  ne: { col: 5, row: 2 },
  ar: { col: 5, row: 3 },
  la: { col: 5, row: 4 },

  wi: { col: 6, row: 0 },
  il: { col: 6, row: 1 },
  mo: { col: 6, row: 2 },
  tn: { col: 6, row: 3 },
  ms: { col: 6, row: 4 },

  mi: { col: 7, row: 0 },
  in: { col: 7, row: 1 },
  ky: { col: 7, row: 2 },
  al: { col: 7, row: 4 },

  oh: { col: 8, row: 1 },
  wv: { col: 8, row: 2 },
  va: { col: 8, row: 3 },
  nc: { col: 8, row: 4 },
  ga: { col: 8, row: 5 },

  ny: { col: 9, row: 0 },
  pa: { col: 9, row: 1 },
  nj: { col: 9, row: 2 },
  md: { col: 9, row: 3 },
  sc: { col: 9, row: 4 },
  fl: { col: 9, row: 5 },

  vt: { col: 10, row: 0 },
  ma: { col: 10, row: 1 },
  ct: { col: 10, row: 2 },
  de: { col: 10, row: 3 },

  me: { col: 11, row: 0 },
  nh: { col: 11, row: 1 },
  ri: { col: 11, row: 2 },
};

// Hand-authored silhouettes for the handful of states whose outline is
// iconic enough that a generic rectangle would look obviously wrong --
// 'X' is a filled district cell, any other character is empty. Row/column
// position is literal (not auto-centered), so panhandles/tails can be
// offset relative to the state's main body the way they really are (e.g.
// FL's panhandle sits north-west of its peninsula, not centered above it).
// Cell counts are hand-matched to each state's real district count; if
// that ever drifts (redistricting), reconcileCellCount pads/trims safely.
const STATE_MASKS: Record<string, string[]> = {
  // Texas (38): narrow panhandle, wide body, tapering to the Rio Grande Valley.
  tx: ["...XX...", "..XXXX..", ".XXXXX..", "XXXXXX..", "XXXXXXX.", ".XXXXXX.", "..XXXX..", "...XXX..", "....X..."],
  // Florida (28): panhandle to the west, peninsula + Keys trailing south-east.
  fl: [
    "XXXXX...",
    "XXXXX...",
    "....XXX.",
    ".....XX.",
    ".....XXXX",
    ".....XXX",
    ".....XX.",
    ".....XX.",
    "......X.",
    "......X.",
  ],
  // Michigan (13): the mitten, with a thumb bump on the east side.
  mi: ["XXX.", "XXXX", "XXXX", "XX.."],
  // Oklahoma (5): panhandle to the west, main body to the east.
  ok: ["XX..", ".XXX"],
  // Louisiana (6): wide north, boot toe narrowing south.
  la: ["XXXX", ".XX."],
  // California (52): long north-south coastal crescent, bulging toward LA in the south.
  ca: [
    ".XXX.",
    ".XXXX",
    "XXXXXX",
    "XXXXXX",
    "XXXXXX",
    "XXXXXX",
    "XXXXX.",
    ".XXXX.",
    ".XXXX.",
    "XXXXXX",
    ".XX...",
  ],
  // New York (26): wide upstate mass, Long Island trailing south-east.
  ny: ["XXXXXX.", "XXXXXX.", "XXXXXX.", "XXXXX..", ".....XX", "......X"],
};

// Real-shape width:height ratio for every other state -- drives a plain
// tapered rectangle instead of a hand-authored mask, still far closer to
// reality than a circular blob (e.g. TN/KY read as wide and flat, IL/NJ
// read as tall and narrow). States not listed default to roughly square.
const STATE_ASPECT: Record<string, number> = {
  al: 0.55, ak: 1, az: 0.85, ar: 1.15, co: 1.35, ct: 2, de: 0.4,
  ga: 0.85, hi: 1.4, id: 0.5, il: 0.55, in: 0.75, ia: 1.4, ks: 1.9,
  ky: 2.6, me: 0.85, md: 2.2, ma: 2.3, mn: 0.7, ms: 0.55, mo: 1.4,
  mt: 1.9, ne: 2.3, nv: 0.6, nh: 0.8, nj: 0.55, nm: 0.75, nc: 2.5,
  nd: 1.5, oh: 1.2, or: 1.35, pa: 2.1, ri: 1, sc: 1.6, sd: 1.7,
  tn: 3, ut: 0.75, vt: 0.65, va: 2, wa: 1.35, wv: 1.2, wi: 0.85, wy: 1.05,
};

// -- Pointy-top hex grid, "offset row" coordinates -------------------------
// HEX_SIZE is the hex's circumradius (center to vertex); using it directly as
// the polygon radius means adjacent hexes tile edge-to-edge with no gap math
// required elsewhere. Cell positions are (row, col) with odd rows shoved
// right by half a column -- standard pointy-top offset tiling -- and col may
// be fractional (used to center a short row under a wider one above it).
const HEX_SIZE = 1;
const SQRT3 = Math.sqrt(3);

function offsetToLocalPixel(row: number, col: number): [number, number] {
  const shove = row % 2 !== 0 ? 0.5 : 0;
  const x = HEX_SIZE * SQRT3 * (col + shove);
  const y = HEX_SIZE * 1.5 * row;
  return [x, y];
}

interface Cell {
  row: number;
  col: number;
}

function cellsFromMask(mask: string[]): Cell[] {
  const cells: Cell[] = [];
  mask.forEach((line, row) => {
    for (let col = 0; col < line.length; col++) {
      if (line[col] === "X") cells.push({ row, col });
    }
  });
  return cells;
}

/** A plain tapered rectangle sized to the given aspect ratio -- short last
 * row is centered under the rows above rather than left-hanging ragged.
 * The centering offset is rounded to a whole column (never a fractional
 * half-column): offsetToLocalPixel's row-parity shove already alternates
 * each row by exactly half a column to make hexagons interlock, and that
 * alternation only stays intact if every row's *additional* shift is a
 * whole-column multiple -- a fractional centering offset can cancel or
 * double the shove instead of adding to it, landing the row a full column
 * off from where it should nest and reading as visibly "unaligned" (seen
 * on CT, IL, MA, whose last row is short by an odd number of cells). */
function cellsFromAspect(n: number, aspect: number): Cell[] {
  const cols = Math.max(1, Math.round(Math.sqrt(n * aspect)));
  const cells: Cell[] = [];
  let remaining = n;
  for (let row = 0; remaining > 0; row++) {
    const count = Math.min(cols, remaining);
    const offset = Math.round((cols - count) / 2);
    for (let c = 0; c < count; c++) cells.push({ row, col: c + offset });
    remaining -= count;
  }
  return cells;
}

/** Pads/trims a shape's cell list to exactly n cells -- a safety net in case
 * a hand-authored mask's count ever drifts from the real district count
 * (e.g. redistricting), so a mismatch degrades gracefully instead of
 * mis-rendering. */
function reconcileCellCount(cells: Cell[], n: number): Cell[] {
  if (cells.length === n) return cells;
  if (cells.length > n) return cells.slice(0, n);
  const maxRow = cells.reduce((m, c) => Math.max(m, c.row), -1);
  const rowWidth = Math.max(1, Math.round(cells.length / (maxRow + 1)));
  const result = [...cells];
  let row = maxRow + 1;
  let remaining = n - cells.length;
  while (remaining > 0) {
    const count = Math.min(rowWidth, remaining);
    const offset = Math.round((rowWidth - count) / 2);
    for (let c = 0; c < count; c++) result.push({ row, col: c + offset });
    remaining -= count;
    row++;
  }
  return result;
}

function stateShapeCells(stateCode: string, n: number): Cell[] {
  const mask = STATE_MASKS[stateCode];
  const raw = mask ? cellsFromMask(mask) : cellsFromAspect(n, STATE_ASPECT[stateCode] ?? 1);
  return reconcileCellCount(raw, n);
}

function hexPolygonPoints(cx: number, cy: number, size: number): string {
  const points: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    points.push(`${(cx + size * Math.cos(angle)).toFixed(2)},${(cy + size * Math.sin(angle)).toFixed(2)}`);
  }
  return points.join(" ");
}

interface PlacedDistrict extends HouseDistrictRef {
  cx: number;
  cy: number;
}

interface StateLabel {
  stateCode: string;
  x: number;
  y: number;
}

// Gap left between neighboring state clusters' bounding boxes, in HEX_SIZE
// units -- keeps clusters visually distinct without wasting space, since
// column/row extents below are shrink-wrapped per state rather than a fixed
// grid pitch (a fixed pitch has to assume worst-case for CA/TX-sized
// clusters everywhere, which wastes most of the canvas around 1-district
// states and makes every hexagon smaller than it needs to be).
const CLUSTER_GAP_X = 0.9;
const CLUSTER_GAP_Y = 0.25;
const EMPTY_BAND_SIZE = 1.6;
// State-code label sizing -- reserved as extra headroom above each row of
// clusters (see rowHalfExtent below) so a bigger label never overlaps the
// row above it even as CLUSTER_GAP_Y shrinks.
const LABEL_FONT_SIZE = HEX_SIZE * 1.6;
const LABEL_HEADROOM = LABEL_FONT_SIZE * 0.85;

function layoutDistricts(districts: HouseDistrictRef[]): { placed: PlacedDistrict[]; labels: StateLabel[] } {
  const byState = new Map<string, HouseDistrictRef[]>();
  for (const d of districts) {
    const key = d.stateCode.toLowerCase();
    const list = byState.get(key);
    if (list) list.push(d);
    else byState.set(key, [d]);
  }

  // Pass 1: build each state's own hex cluster, centered on its own local
  // origin, and record its half-extent in x/y for grid sizing below.
  interface StateCluster {
    stateCode: string;
    col: number;
    row: number;
    cells: { cx: number; cy: number; slug: string }[];
    halfWidth: number;
    halfHeight: number;
    topY: number;
  }
  const clusters: StateCluster[] = [];

  for (const [stateCode, list] of byState) {
    const anchor = STATE_GRID_POSITION[stateCode];
    if (!anchor) continue;

    const sorted = [...list].sort((a, b) => districtNumber(a.slug) - districtNumber(b.slug));
    const shape = stateShapeCells(stateCode, sorted.length);
    const rawPoints = shape.map(({ row, col }) => offsetToLocalPixel(row, col));

    const xs = rawPoints.map(([x]) => x);
    const ys = rawPoints.map(([, y]) => y);
    const centerX = (Math.min(...xs) + Math.max(...xs)) / 2;
    const centerY = (Math.min(...ys) + Math.max(...ys)) / 2;

    const cells = sorted.map((district, i) => {
      const [x, y] = rawPoints[i];
      return { cx: x - centerX, cy: y - centerY, slug: district.slug };
    });

    clusters.push({
      stateCode,
      col: anchor.col,
      row: anchor.row,
      cells,
      halfWidth: Math.max(...xs) - centerX + HEX_SIZE,
      halfHeight: Math.max(...ys) - centerY + HEX_SIZE,
      topY: Math.min(...ys) - centerY,
    });
  }

  // Pass 2: size each grid column/row to the widest/tallest cluster it
  // contains, then lay columns/rows out edge-to-edge (plus a fixed gap) so
  // the whole map shrink-wraps to actual content instead of a fixed pitch.
  const maxCol = Math.max(0, ...clusters.map((c) => c.col));
  const maxRow = Math.max(0, ...clusters.map((c) => c.row));

  const colHalfExtent = new Array(maxCol + 1).fill(EMPTY_BAND_SIZE / 2);
  const rowHalfExtent = new Array(maxRow + 1).fill(EMPTY_BAND_SIZE / 2);
  for (const c of clusters) {
    colHalfExtent[c.col] = Math.max(colHalfExtent[c.col], c.halfWidth);
    rowHalfExtent[c.row] = Math.max(rowHalfExtent[c.row], c.halfHeight + LABEL_HEADROOM);
  }

  const colCenter = new Array(maxCol + 1).fill(0);
  for (let c = 1; c <= maxCol; c++) {
    colCenter[c] = colCenter[c - 1] + colHalfExtent[c - 1] + CLUSTER_GAP_X + colHalfExtent[c];
  }
  const rowCenter = new Array(maxRow + 1).fill(0);
  for (let r = 1; r <= maxRow; r++) {
    rowCenter[r] = rowCenter[r - 1] + rowHalfExtent[r - 1] + CLUSTER_GAP_Y + rowHalfExtent[r];
  }

  const placed: PlacedDistrict[] = [];
  const labels: StateLabel[] = [];
  for (const cluster of clusters) {
    const anchorX = colCenter[cluster.col];
    const anchorY = rowCenter[cluster.row];
    for (const cell of cluster.cells) {
      placed.push({ slug: cell.slug, stateCode: cluster.stateCode, cx: anchorX + cell.cx, cy: anchorY + cell.cy });
    }
    labels.push({ stateCode: cluster.stateCode, x: anchorX, y: anchorY + cluster.topY - LABEL_FONT_SIZE * 0.7 });
  }

  return { placed, labels };
}

export function HouseDistrictMap({ districts, visualsBySlug, onDistrictClick, getTooltip }: HouseDistrictMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, containerWidth: 0, containerHeight: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltip = hovered ? getTooltip?.(hovered) ?? null : null;

  const { placed, labels, viewBox } = useMemo(() => {
    const { placed, labels } = layoutDistricts(districts);
    if (placed.length === 0) {
      return { placed, labels, viewBox: "0 0 100 100" };
    }
    const pad = HEX_SIZE * 1.2;
    const xs = placed.map((p) => p.cx);
    const ys = placed.map((p) => p.cy);
    const minX = Math.min(...xs) - pad;
    const maxX = Math.max(...xs) + pad;
    const minY = Math.min(...ys.concat(labels.map((l) => l.y))) - pad;
    const maxY = Math.max(...ys) + pad;
    return { placed, labels, viewBox: `${minX} ${minY} ${maxX - minX} ${maxY - minY}` };
  }, [districts]);

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
  const anchorBottom = mousePos.y > mousePos.containerHeight / 2;
  const tooltipStyle = {
    ...(anchorRight
      ? { right: mousePos.containerWidth - mousePos.x + TOOLTIP_OFFSET }
      : { left: mousePos.x + TOOLTIP_OFFSET }),
    ...(anchorBottom
      ? { bottom: mousePos.containerHeight - mousePos.y + TOOLTIP_OFFSET }
      : { top: mousePos.y + TOOLTIP_OFFSET }),
  };

  return (
    <div ref={containerRef} className="relative">
      <svg viewBox={viewBox} role="img" aria-label="Hexagon map of U.S. congressional districts" className="w-full">
        <defs>
          {PARTY_SLUGS.flatMap((slug) =>
            TIERS.map((tier) => (
              <pattern
                key={stripePatternId(slug, tier)}
                id={stripePatternId(slug, tier)}
                width="3"
                height="3"
                patternTransform="rotate(45)"
                patternUnits="userSpaceOnUse"
              >
                <rect width="3" height="3" fill={`var(--party-${slug}-${tier})`} />
                <line x1="0" y1="0" x2="0" y2="3" stroke="var(--surface)" strokeWidth="1.1" />
              </pattern>
            ))
          )}
        </defs>
        {labels.map((label) => (
          <text
            key={label.stateCode}
            x={label.x}
            y={label.y}
            textAnchor="middle"
            fontSize={LABEL_FONT_SIZE}
            fontWeight={600}
            fill="var(--text-muted)"
            style={{ pointerEvents: "none" }}
          >
            {label.stateCode.toUpperCase()}
          </text>
        ))}
        {placed.map(({ slug, cx, cy }) => {
          const visual = visualsBySlug[slug];
          const tier = visual ? probabilityTier(visual.party, visual.winProbability) : null;
          const fill =
            tier == null
              ? "var(--gridline)"
              : visual!.isFlip
                ? `url(#${stripePatternId(tier.slug, tier.tier)})`
                : `var(--party-${tier.slug}-${tier.tier})`;
          const clickable = Boolean(visual);

          return (
            <polygon
              key={slug}
              points={hexPolygonPoints(cx, cy, HEX_SIZE * 0.97)}
              fill={fill}
              stroke="var(--surface)"
              strokeWidth={0.06}
              style={{
                cursor: clickable ? "pointer" : "default",
                opacity: hovered === slug ? 0.8 : 1,
                transition: "opacity 100ms ease",
              }}
              onMouseEnter={(e) => {
                setHovered(slug);
                updateMousePos(e);
              }}
              onMouseMove={updateMousePos}
              onMouseLeave={() => setHovered(null)}
              onClick={() => clickable && onDistrictClick(slug)}
            />
          );
        })}
      </svg>
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border px-3 py-2 text-sm shadow-md"
          style={{
            ...tooltipStyle,
            backgroundColor: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            minWidth: "180px",
          }}
        >
          <div className="font-medium">{tooltip.title}</div>
          {tooltip.candidates && tooltip.candidates.length > 0 ? (
            <div className="mt-1 flex flex-col gap-1">
              {tooltip.candidates.map((c) => (
                <div key={c.name} className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-flex h-4 w-4 flex-shrink-0 items-center justify-center text-[9px] font-bold text-white"
                      style={{ backgroundColor: partyColorVar(c.party) }}
                    >
                      {partyAbbrev(c.party)}
                    </span>
                    <span style={{ color: "var(--text-secondary)" }}>{c.name}</span>
                  </span>
                  <span className="font-semibold tabular-nums">{c.voteShare.toFixed(1)}%</span>
                </div>
              ))}
              {tooltip.winner && (
                <div
                  className="mt-1 border-t pt-1 text-xs"
                  style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                >
                  <span className="font-semibold" style={{ color: partyColorVar(tooltip.winner.party) }}>
                    {tooltip.winner.name}
                  </span>{" "}
                  projected to win{" "}
                  <span style={{ color: partyColorVar(tooltip.winner.party) }}>
                    ({formatWinProbability(tooltip.winner.probability)})
                  </span>
                </div>
              )}
              {tooltip.candidates.length >= 2 &&
                (() => {
                  const byShareDesc = [...tooltip.candidates!].sort((a, b) => b.voteShare - a.voteShare);
                  const leader = byShareDesc[0];
                  const margin = leader.voteShare - byShareDesc[1].voteShare;
                  return (
                    <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                      Margin:{" "}
                      <span className="font-semibold tabular-nums" style={{ color: partyColorVar(leader.party) }}>
                        {partyAbbrev(leader.party)} +{margin.toFixed(1)}
                      </span>
                    </div>
                  );
                })()}
            </div>
          ) : (
            <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              No forecast yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
