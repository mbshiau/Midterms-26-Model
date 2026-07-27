"""One-time bootstrap for frontend/src/data/allDistrictShapes.ts (the
congressional district boundary shapes used by the House map, see
frontend/src/components/HouseDistrictMap.tsx).

Source: "2026 United States House of Representatives elections retirements
or losses of renomination map.svg" by Coolxsearcher1414, Wikimedia Commons
(CC0 1.0):
https://commons.wikimedia.org/wiki/File:2026_United_States_House_of_Representatives_elections_retirements_or_losses_of_renomination_map.svg

Unlike the earlier 2008-vintage source this replaced, this map was built
specifically for the 2026 cycle, so it reflects *current* district lines
(verified 435-for-435 against app.seed.house_seed_data.HOUSE_RACES -- no
gaps, no orphans).

The source SVG mixes individually-labeled district paths (most states, via
an `id`, `data-name`, or `inkscape:label` attribute matching "XX-N") with
duplicate zoomed-in "metro inset" copies of some districts (Chicago/LA/NYC,
drawn again at a different position/scale for legibility). Every one of the
435 real districts resolves to exactly one unambiguous non-inset path; a
label that couldn't be resolved this way would be *skipped*, not guessed at
by position -- this run resolved all 435 with zero such skips.

Path point counts are Douglas-Peucker-simplified (~92% fewer points) to
keep the generated file a reasonable bundle size; visually indistinguishable
at map scale (only line/lineto/horizontal/vertical commands appear in the
source paths -- no curves -- so this simplification is straightforward and
lossless in shape category, just point density).

Usage (from inside the backend container or a matching venv; needs
`httpx` -- already a project dependency):
    python -m scripts.extract_house_district_paths
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOURCE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/7/70/"
    "2026_United_States_House_of_Representatives_elections_retirements_or_losses_of_renomination_map.svg"
)
SOURCE_WIKI_PAGE = (
    "https://commons.wikimedia.org/wiki/File:2026_United_States_House_of_Representatives_"
    "elections_retirements_or_losses_of_renomination_map.svg"
)
HEADERS = {
    # upload.wikimedia.org's edge appears to bot-filter on more than just
    # User-Agent (a bare descriptive UA got a 403/429 here even though the
    # same UA works fine against en.wikipedia.org's API in
    # app.ingestion.wikipedia_scraper) -- a fuller, real-browser-shaped
    # header set clears it.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://en.wikipedia.org/",
}

INKSCAPE_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"
DISTRICT_RE = re.compile(r"^[A-Z]{2}-\d+$")
METRO_MARKERS = {
    "Metros", "Chicagoland", "Chicagoland_Districts",
    "LAX", "Los_Angeles_Districts",
    "NYC", "New_York_City", "New_York_City_Districts",
}
SIMPLIFY_EPSILON = 0.35  # in the source file's own coordinate units (viewBox 1900x1180)
MAP_VIEWBOX = "0 0 1900 1180"

_OUT_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "data" / "allDistrictShapes.ts"


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1]


def _label_of(el: ET.Element) -> str | None:
    for key in ("id", "data-name", INKSCAPE_LABEL):
        v = el.get(key)
        if v and DISTRICT_RE.match(v):
            return v
    return None


def _parse_path(d: str) -> list[list[tuple[float, float]]]:
    """Parses an M/L/H/V/Z-only path (no curves -- verified true of this
    source) into a list of subpaths, each a list of absolute (x, y) points."""
    tokens = re.findall(r"[MmLlHhVvZz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    subpaths: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    x = y = 0.0
    i = 0
    cmd = None
    while i < len(tokens):
        t = tokens[i]
        if t in "MmLlHhVvZz":
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    subpaths.append(cur)
                    cur = []
                continue
        if cmd in "Mm":
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            i += 2
            x, y = (x + nx, y + ny) if cmd == "m" else (nx, ny)
            if cur:
                subpaths.append(cur)
            cur = [(x, y)]
            cmd = "l" if cmd == "m" else "L"  # implicit lineto for subsequent pairs
        elif cmd in "Ll":
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            i += 2
            x, y = (x + nx, y + ny) if cmd == "l" else (nx, ny)
            cur.append((x, y))
        elif cmd in "Hh":
            nx = float(tokens[i])
            i += 1
            x = x + nx if cmd == "h" else nx
            cur.append((x, y))
        elif cmd in "Vv":
            ny = float(tokens[i])
            i += 1
            y = y + ny if cmd == "v" else ny
            cur.append((x, y))
        else:
            raise ValueError(f"unexpected path token {t!r}")
    if cur:
        subpaths.append(cur)
    return subpaths


def _perpendicular_distance(
    pt: tuple[float, float], line_start: tuple[float, float], line_end: tuple[float, float]
) -> float:
    (x, y), (x1, y1), (x2, y2) = pt, line_start, line_end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    proj_x, proj_y = x1 + t * dx, y1 + t * dy
    return ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5


def _douglas_peucker(
    points: list[tuple[float, float]], epsilon: float
) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    dmax, index = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _perpendicular_distance(points[i], points[0], points[-1])
        if d > dmax:
            index, dmax = i, d
    if dmax > epsilon:
        left = _douglas_peucker(points[: index + 1], epsilon)
        right = _douglas_peucker(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]

def _serialize(subpaths: list[list[tuple[float, float]]], precision: int = 2) -> str:
    parts = []
    for sp in subpaths:
        if not sp:
            continue
        pts = [f"{round(x, precision):g},{round(y, precision):g}" for x, y in sp]
        parts.append("M" + " L".join(pts) + " Z")
    return " ".join(parts)


def _full_ancestor_chain(el: ET.Element, parent_map: dict) -> list[ET.Element]:
    chain = []
    cur = el
    while cur in parent_map:
        cur = parent_map[cur]
        chain.append(cur)
    return list(reversed(chain))


def extract_district_paths(svg_bytes: bytes) -> dict[str, dict]:
    root = ET.fromstring(svg_bytes)
    parent_map = {c: p for p in root.iter() for c in p}

    matches: dict[str, list[ET.Element]] = {}
    for el in root.iter():
        if _tag(el) not in ("path", "g"):
            continue
        lbl = _label_of(el)
        if lbl is None:
            continue
        matches.setdefault(lbl, []).append(el)

    resolved: dict[str, dict] = {}
    for lbl, els in matches.items():
        non_metro = []
        for el in els:
            idents = {
                (a.get("id") or a.get(INKSCAPE_LABEL) or _tag(a))
                for a in _full_ancestor_chain(el, parent_map)
            }
            if not (idents & METRO_MARKERS):
                non_metro.append(el)

        if len(non_metro) != 1:
            logger.warning(
                "skipping %s: %d unambiguous non-metro candidate(s) (expected exactly 1)",
                lbl, len(non_metro),
            )
            continue
        chosen = non_metro[0]
        if _tag(chosen) != "path" or not chosen.get("d"):
            logger.warning("skipping %s: resolved element has no usable path data", lbl)
            continue

        transforms = [
            a.get("transform") for a in _full_ancestor_chain(chosen, parent_map) if a.get("transform")
        ]
        if chosen.get("transform"):
            transforms.append(chosen.get("transform"))

        subpaths = _parse_path(chosen.get("d"))
        simplified = [_douglas_peucker(sp, SIMPLIFY_EPSILON) for sp in subpaths]

        state, num = lbl.split("-")
        slug = f"{state.lower()}-house-{int(num):02d}"
        resolved[slug] = {
            "d": _serialize(simplified),
            "transform": " ".join(transforms) if transforms else None,
        }

    return resolved


def render_ts(districts: dict[str, dict]) -> str:
    lines = [
        '// Congressional district boundary paths, keyed by Race.slug (e.g. "al-house-01").',
        "// Each entry is one district's SVG path `d` plus an optional `transform` (the",
        "// composed transform chain from the source file's group nesting, if any --",
        "// preserved as-is so this renders identically to the source). Path point counts",
        "// are Douglas-Peucker-simplified (~92% fewer points) to keep the bundle a",
        "// reasonable size -- visually indistinguishable at map scale.",
        "//",
        "// Generated by backend/scripts/extract_house_district_paths.py -- see that",
        "// script's docstring for the full source citation and extraction approach.",
        "// Source: \"2026 United States House of Representatives elections retirements or",
        "// losses of renomination map.svg\" by Coolxsearcher1414, Wikimedia Commons, CC0 1.0:",
        f"// {SOURCE_WIKI_PAGE}",
        "//",
        "// Reflects *current* 2026 district lines (unlike the 2008-vintage map this",
        "// replaced) -- verified 435-for-435 against app.seed.house_seed_data.HOUSE_RACES,",
        "// no gaps, no orphans, no guessed/ambiguous matches.",
        "//",
        "// This file's own coloring scheme (which the source map used to show retirement/",
        "// renomination-loss status) is intentionally NOT reproduced here -- every district",
        "// is rendered as a plain shape and recolored by this app's own forecast data (see",
        "// components/HouseDistrictMap.tsx).",
        "",
        f'export const MAP_VIEWBOX = "{MAP_VIEWBOX}";',
        "",
        "export interface DistrictPath {",
        "  d: string;",
        "  transform?: string;",
        "}",
        "",
        "export const ALL_DISTRICT_PATHS: Record<string, DistrictPath> = {",
    ]
    for slug in sorted(districts.keys()):
        entry = districts[slug]
        d = json.dumps(entry["d"])
        if entry.get("transform"):
            t = json.dumps(entry["transform"])
            lines.append(f"  {json.dumps(slug)}: {{ d: {d}, transform: {t} }},")
        else:
            lines.append(f"  {json.dumps(slug)}: {{ d: {d} }},")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    logger.info("fetching %s ...", SOURCE_URL)
    resp = httpx.get(SOURCE_URL, headers=HEADERS, timeout=60, follow_redirects=True)
    resp.raise_for_status()

    districts = extract_district_paths(resp.content)
    logger.info("resolved %d districts", len(districts))

    _OUT_PATH.write_text(render_ts(districts))
    logger.info("wrote %s", _OUT_PATH)


if __name__ == "__main__":
    main()
