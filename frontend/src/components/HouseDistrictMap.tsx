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
  az: { col: 2, row: 4 },

  // CO belongs in the MT/WY/UT/NM chain (it's directly south of WY, same
  // longitude band as UT/NM), not grouped with ND/KS/OK/TX to its east.
  mt: { col: 3, row: 0 },
  wy: { col: 3, row: 1 },
  ut: { col: 3, row: 2 },
  co: { col: 3, row: 3 },
  nm: { col: 3, row: 5 },

  // Starting one row lower than WA/MT/MN's row 0 (ND isn't really that far
  // north) also carries TX -- last in this column -- further down, closer
  // to level with FL/GA.
  nd: { col: 4, row: 1 },
  sd: { col: 4, row: 2 },
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

  // FL stacks directly under GA (same column) instead of sharing NY/PA/NJ's
  // column further east -- puts it back under the rest of the Southeast
  // instead of floating off to the right on its own.
  oh: { col: 8, row: 1 },
  wv: { col: 8, row: 2 },
  va: { col: 8, row: 3 },
  nc: { col: 8, row: 4 },
  ga: { col: 8, row: 5 },
  fl: { col: 8, row: 6 },

  ny: { col: 9, row: 0 },
  pa: { col: 9, row: 1 },
  nj: { col: 9, row: 2 },
  md: { col: 9, row: 3 },
  sc: { col: 9, row: 4 },

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
// Full elongation, true to each state's real proportions -- safe to do
// since layoutDistricts stacks columns independently (masonry-style): a
// tall cluster like CA only pushes on whatever's stacked below it in its
// *own* column (here, nothing -- WA/OR are above it), never on neighboring
// columns. That's what lets it "wrap" to as many rows as its real shape
// needs without forcing the rest of the map to also get taller.
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
  // California (52): long north-south coastal crescent -- the southern third
  // (LA/San Diego) bends progressively east, same as the real coastline,
  // which also closes up the empty gap that otherwise opens between CA's
  // column and TX/OK below it.
  ca: [
    ".XXX.",
    ".XXXX",
    "XXXXX",
    "XXXXX",
    "XXXXX",
    "XXXXX",
    "XXXXX",
    ".XXXX",
    "..XX.",
    "..XXX.",
    "...XXXX",
    "...XXXXX",
    "....XX.",
  ],
  // New York (26): wide upstate mass, Long Island trailing south-east.
  ny: ["XXXXXX.", "XXXXXX.", "XXXXXX.", "XXXXX..", ".....XX", "......X"],
};

// Real-shape width:height ratio for every other state -- drives a plain
// tapered rectangle instead of a hand-authored mask, still far closer to
// reality than a circular blob (e.g. TN/KY read as wide and flat, IL/NJ
// read as tall and narrow). States not listed default to roughly square.
const STATE_ASPECT: Record<string, number> = {
  al: 0.45, ak: 1, az: 0.85, ar: 1.15, co: 1.35, ct: 2, de: 0.4,
  ga: 0.85, hi: 1.4, id: 0.4, il: 0.4, in: 0.75, ia: 1.4, ks: 1.9,
  ky: 2.6, me: 0.85, md: 2.2, ma: 2.3, mn: 0.6, ms: 0.45, mo: 1.4,
  mt: 1.9, ne: 2.3, nv: 0.5, nh: 0.8, nj: 0.45, nm: 0.75, nc: 2.5,
  nd: 1.5, oh: 1.2, or: 1.35, pa: 2.1, ri: 1, sc: 1.6, sd: 1.7,
  tn: 3, ut: 0.65, vt: 0.65, va: 2, wa: 1.2, wv: 1.2, wi: 0.7, wy: 1.05,
};

// -- Pointy-top hex grid, "offset row" coordinates -------------------------
// HEX_SIZE is the hex's circumradius (center to vertex); using it directly as
// the polygon radius means adjacent hexes tile edge-to-edge with no gap math
// required elsewhere. Cell positions are (row, col) with odd rows shoved
// right by half a column -- standard pointy-top offset tiling -- and col may
// be fractional (used to center a short row under a wider one above it).
const HEX_SIZE = 21;
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
  // A very "tall" aspect ratio combined with a small n can round down to a
  // single column -- a needlessly tall 1-wide tower for just a handful of
  // districts (seen on MS: 4 districts, aspect 0.55) -- so floor at 2
  // columns once there's enough cells to make a column worth having.
  const cols = Math.max(n >= 3 ? 2 : 1, Math.round(Math.sqrt(n * aspect)));
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

// Gap kept between neighboring state clusters' bounding boxes.
const CLUSTER_GAP = HEX_SIZE * 1.5;
// Extra gap inserted before specific states on top of the normal
// CLUSTER_GAP -- masonry stacking only lets a state's *own* row number set
// where its whole column starts (see layoutDistricts), so nudging a state
// that isn't first in its column further south needs an explicit bump
// like this rather than just editing STATE_GRID_POSITION's row.
const STATE_EXTRA_GAP_BEFORE: Record<string, number> = {
  az: HEX_SIZE * 1.5,
  nm: HEX_SIZE * 1.5,
};
// A column with no states in it (there are none currently, but this is the
// fallback if that ever changes) reserves this much width rather than 0.
const EMPTY_BAND_SIZE = HEX_SIZE;
// STATE_GRID_POSITION's "row" only sets each column's *starting* height
// (see the masonry stacking in layoutDistricts) -- this pitch just needs to
// be a reasonable per-row scale for that starting offset, not an actual
// per-state height, so it stays fixed regardless of any one state's size.
const ANCHOR_PITCH_Y = HEX_SIZE * 3.4;
// State-code label sizing.
const LABEL_FONT_SIZE = HEX_SIZE * 1.45;
// Every state code is 2 characters -- a rough half-width/half-height
// estimate (average bold-glyph advance ~0.62em per character) used both to
// keep a label's own footprint clear of other clusters and to size the
// viewBox so an edge label (e.g. AK, a single hex under a 2-character
// label) never gets clipped.
const LABEL_HALF_WIDTH = LABEL_FONT_SIZE * 0.62;
const LABEL_HALF_HEIGHT = LABEL_FONT_SIZE * 0.5;
const LABEL_ASCENDER = LABEL_FONT_SIZE * 0.8;
const LABEL_GAP = HEX_SIZE * 0.35;

interface StateCluster {
  stateCode: string;
  col: number;
  row: number;
  x: number;
  y: number;
  cells: { cx: number; cy: number; slug: string }[];
  // Distance from the cluster's centroid to each edge -- kept separately
  // (not just a single symmetric halfWidth/halfHeight) because centroid
  // centering makes lopsided shapes (e.g. a bent state) genuinely
  // asymmetric: the true left edge and right edge are not equidistant from
  // center. A label offset toward the *shorter* side using the longer
  // side's distance overshoots into empty space (this is what made CA's
  // label land too far to the left -- it used the bend's larger rightward
  // extent to offset a leftward-placed label).
  leftExtent: number;
  rightExtent: number;
  topExtent: number;
  bottomExtent: number;
  halfWidth: number;
  halfHeight: number;
}

// Extra clearance required on top of the two boxes' own half-extents --
// without this, two labels (or a label and a cluster) can come out
// "technically" not overlapping by only a couple of units, which reads as
// touching once real glyphs render (a bounding-box estimate is necessarily
// a bit optimistic vs. actual rendered text).
const COLLISION_MARGIN = HEX_SIZE * 0.35;

function boxesOverlap(
  ax: number,
  ay: number,
  ahw: number,
  ahh: number,
  bx: number,
  by: number,
  bhw: number,
  bhh: number
): boolean {
  return Math.abs(ax - bx) < ahw + bhw + COLLISION_MARGIN && Math.abs(ay - by) < ahh + bhh + COLLISION_MARGIN;
}

/** Places a state's label in whichever gap around its cluster is actually
 * clear -- tried in priority order (above, right, left, below, matching
 * where a label most often lands in a hand-drawn hex cartogram) -- rather
 * than a fixed offset that assumes uniform row/column spacing. Checks
 * against every *other* cluster (columns are independent, so a nearby
 * column's cluster can drift to any height -- see the masonry stacking in
 * layoutDistricts) and every label placed so far, since two labels can
 * collide with each other in an open gap even when neither touches a hex
 * cluster. If every direction collides with something (dense regions like
 * New England, where two small clusters can be stacked only a hair apart),
 * picks whichever candidate collides with the *fewest* things rather than
 * blindly defaulting to "above" -- "above" is only a good fallback when it
 * was actually clear, not when every option is bad. */
// States whose label should stay above the cluster even if a lower-
// collision spot exists elsewhere -- CA in particular reads oddly with its
// label off to the side, since its shape is tall and narrow enough that
// "above" is unambiguously where a reader expects the name.
const STATE_LABEL_FORCE_ABOVE = new Set(["ca"]);

function placeLabel(cluster: StateCluster, allClusters: StateCluster[], placedLabels: StateLabel[]): StateLabel {
  const others = allClusters.filter((c) => c !== cluster);
  // Each direction is tried at increasing distance (1x, then 1.6x the base
  // gap) before moving to the next direction -- in a dense pocket (New
  // England, where several tiny clusters are stacked only CLUSTER_GAP
  // apart) the nearest slot in every direction can be blocked, but backing
  // further away from the cluster often clears it without abandoning the
  // preferred side.
  const distanceScales = [1, 1.6, 2.4, 3.5, 5];
  const candidates: { x: number; y: number }[] = [];
  for (const distanceScale of distanceScales) {
    const gap = LABEL_GAP * distanceScale;
    candidates.push({ x: cluster.x, y: cluster.y - cluster.topExtent - gap - LABEL_ASCENDER * 0.5 }); // above
    if (STATE_LABEL_FORCE_ABOVE.has(cluster.stateCode)) continue;
    candidates.push(
      { x: cluster.x + cluster.rightExtent + gap + LABEL_HALF_WIDTH, y: cluster.y + LABEL_FONT_SIZE * 0.35 }, // right
      { x: cluster.x - cluster.leftExtent - gap - LABEL_HALF_WIDTH, y: cluster.y + LABEL_FONT_SIZE * 0.35 }, // left
      { x: cluster.x, y: cluster.y + cluster.bottomExtent + gap + LABEL_ASCENDER }, // below
      // A cluster boxed in on all 4 cardinal sides (surrounded by taller
      // neighbors on its own two masonry-column sides, plus its own column
      // neighbors above/below) can still have open diagonal corners.
      {
        x: cluster.x + cluster.rightExtent * 0.6 + gap + LABEL_HALF_WIDTH,
        y: cluster.y - cluster.topExtent - gap * 0.5,
      },
      {
        x: cluster.x - cluster.leftExtent * 0.6 - gap - LABEL_HALF_WIDTH,
        y: cluster.y - cluster.topExtent - gap * 0.5,
      }
    );
  }

  let best = candidates[0];
  let bestCollisions = Infinity;
  for (const candidate of candidates) {
    const candidateCenterY = candidate.y - LABEL_HALF_HEIGHT;
    const clusterCollisions = others.filter((other) =>
      boxesOverlap(
        candidate.x,
        candidateCenterY,
        LABEL_HALF_WIDTH,
        LABEL_HALF_HEIGHT,
        other.x,
        other.y,
        other.halfWidth,
        other.halfHeight
      )
    ).length;
    const labelCollisions = placedLabels.filter((other) =>
      boxesOverlap(
        candidate.x,
        candidateCenterY,
        LABEL_HALF_WIDTH,
        LABEL_HALF_HEIGHT,
        other.x,
        other.y - LABEL_HALF_HEIGHT,
        LABEL_HALF_WIDTH,
        LABEL_HALF_HEIGHT
      )
    ).length;
    const totalCollisions = clusterCollisions + labelCollisions;
    if (totalCollisions === 0) return { stateCode: cluster.stateCode, x: candidate.x, y: candidate.y };
    if (totalCollisions < bestCollisions) {
      bestCollisions = totalCollisions;
      best = candidate;
    }
  }
  return { stateCode: cluster.stateCode, x: best.x, y: best.y };
}

function layoutDistricts(districts: HouseDistrictRef[]): { placed: PlacedDistrict[]; labels: StateLabel[] } {
  const byState = new Map<string, HouseDistrictRef[]>();
  for (const d of districts) {
    const key = d.stateCode.toLowerCase();
    const list = byState.get(key);
    if (list) list.push(d);
    else byState.set(key, [d]);
  }

  // Pass 1: build each state's own hex cluster, centered on its own local
  // origin, seeded at a tight starting position from STATE_GRID_POSITION.
  const clusters: StateCluster[] = [];

  for (const [stateCode, list] of byState) {
    const anchor = STATE_GRID_POSITION[stateCode];
    if (!anchor) continue;

    const sorted = [...list].sort((a, b) => districtNumber(a.slug) - districtNumber(b.slug));
    const shape = stateShapeCells(stateCode, sorted.length);
    const rawPoints = shape.map(({ row, col }) => offsetToLocalPixel(row, col));

    const xs = rawPoints.map(([x]) => x);
    const ys = rawPoints.map(([, y]) => y);
    // The cluster's own local origin -- and so its label anchor and its
    // column/row's reserved space -- is centered on the *centroid* (mean of
    // all cells) rather than the bounding-box midpoint. For a lopsided
    // shape (e.g. CA's mask, whose southern third bends east to fill the
    // gap toward TX), the bbox midpoint sits well outside where most of the
    // hexagons actually are, which drags the label away from the cluster's
    // visual mass; the centroid stays close to it regardless of a few
    // outlier cells on one side.
    const centerX = xs.reduce((sum, x) => sum + x, 0) / xs.length;
    const centerY = ys.reduce((sum, y) => sum + y, 0) / ys.length;

    const cells = sorted.map((district, i) => {
      const [x, y] = rawPoints[i];
      return { cx: x - centerX, cy: y - centerY, slug: district.slug };
    });

    clusters.push({
      stateCode,
      col: anchor.col,
      row: anchor.row,
      x: 0,
      y: 0,
      cells,
      // Centroid centering means the two sides are no longer symmetric by
      // construction -- track each edge's real distance separately (see
      // StateCluster's docstring) instead of assuming
      // max(xs)-center == center-min(xs).
      leftExtent: centerX - Math.min(...xs) + HEX_SIZE,
      rightExtent: Math.max(...xs) - centerX + HEX_SIZE,
      topExtent: centerY - Math.min(...ys) + HEX_SIZE,
      bottomExtent: Math.max(...ys) - centerY + HEX_SIZE,
      halfWidth: Math.max(Math.max(...xs) - centerX, centerX - Math.min(...xs)) + HEX_SIZE,
      halfHeight: Math.max(Math.max(...ys) - centerY, centerY - Math.min(...ys)) + HEX_SIZE,
    });
  }

  // Pass 2: x comes from a column's own required width (as before -- a
  // shrink-wrapped grid works fine horizontally, since states rarely vary
  // in width anywhere near as wildly as they do in height).
  const maxCol = Math.max(0, ...clusters.map((c) => c.col));
  const colHalfExtent = new Array(maxCol + 1).fill(EMPTY_BAND_SIZE / 2);
  for (const c of clusters) {
    colHalfExtent[c.col] = Math.max(colHalfExtent[c.col], c.halfWidth, LABEL_HALF_WIDTH);
  }
  const colCenter = new Array(maxCol + 1).fill(0);
  for (let c = 1; c <= maxCol; c++) {
    colCenter[c] = colCenter[c - 1] + colHalfExtent[c - 1] + CLUSTER_GAP + colHalfExtent[c];
  }

  // Pass 3: y comes from stacking each column *independently*, masonry-
  // style -- a state's height only pushes on the next state stacked below
  // it in the very same column, never on neighboring columns. This is what
  // lets CA (column 1, alongside WA/OR) extend well past where a short
  // column like ID/NV/AZ ends, instead of a shared "row" forcing every
  // column to reserve CA-sized vertical space. Each column's first state
  // starts at its nominal row * ANCHOR_PITCH_Y, which keeps columns
  // roughly latitude-aligned at the top even though their total height
  // (and therefore where they end) varies a lot after that.
  const byCol = new Map<number, StateCluster[]>();
  for (const cluster of clusters) {
    const list = byCol.get(cluster.col);
    if (list) list.push(cluster);
    else byCol.set(cluster.col, [cluster]);
  }
  for (const list of byCol.values()) {
    list.sort((a, b) => a.row - b.row);
    list.forEach((cluster, i) => {
      cluster.x = colCenter[cluster.col];
      cluster.y =
        i === 0
          ? cluster.row * ANCHOR_PITCH_Y
          : list[i - 1].y +
            list[i - 1].halfHeight +
            CLUSTER_GAP +
            (STATE_EXTRA_GAP_BEFORE[cluster.stateCode] ?? 0) +
            cluster.halfHeight;
    });
  }

  // Pass 4: place hexes at final cluster positions, then drop each label
  // into whichever surrounding gap is clear.
  const placed: PlacedDistrict[] = [];
  for (const cluster of clusters) {
    for (const cell of cluster.cells) {
      placed.push({ slug: cell.slug, stateCode: cluster.stateCode, cx: cluster.x + cell.cx, cy: cluster.y + cell.cy });
    }
  }
  // Label placement order matters (earlier states get first pick of their
  // preferred "above" slot) -- go top-to-bottom, left-to-right, same
  // reading order a human laying out the map by hand would likely use.
  const labels: StateLabel[] = [];
  const labelOrder = [...clusters].sort((a, b) => a.row - b.row || a.col - b.col);
  for (const cluster of labelOrder) {
    labels.push(placeLabel(cluster, clusters, labels));
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
    const pad = HEX_SIZE * 0.9;
    const xs = placed.map((p) => p.cx);
    const ys = placed.map((p) => p.cy);
    // Edge labels (e.g. AK, a single hex under a 2-character label) can
    // extend further out than any actual hex cell, so the viewBox bounds
    // must account for label width/ascender too, not just hex positions --
    // and since placeLabel can put a label on any of the 4 sides now (not
    // just above), both left/right *and* top/bottom label extents matter.
    const labelLeftXs = labels.map((l) => l.x - LABEL_HALF_WIDTH);
    const labelRightXs = labels.map((l) => l.x + LABEL_HALF_WIDTH);
    const labelTopYs = labels.map((l) => l.y - LABEL_ASCENDER);
    const labelBottomYs = labels.map((l) => l.y + LABEL_FONT_SIZE * 0.4);
    const minX = Math.min(...xs, ...labelLeftXs) - pad;
    const maxX = Math.max(...xs, ...labelRightXs) + pad;
    const minY = Math.min(...ys, ...labelTopYs) - pad;
    const maxY = Math.max(...ys, ...labelBottomYs) + pad;
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
                width="4"
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
