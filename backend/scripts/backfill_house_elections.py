"""One-time backfill of real 2024 `house_elections` history into
app/data/district_fundamentals_data.py, for the handful of states whose own
"2024 United States House of Representatives elections in {state}"
Wikipedia page publishes a single clean per-district summary table (see
app.ingestion.house_scraper.fetch_state_house_results) -- confirmed by hand
to be: Georgia, Michigan, Minnesota, New Mexico, Connecticut. Most other
states spread results across many per-district subsections instead (no
unified table to bulk-parse) and are intentionally left untouched here --
see the project's PVI backfill for how those remain fine with 100% PVI
weight (app.services.fundamentals.district_lean) until filled in by hand or
a future, more involved per-district scraper.

New York and Pennsylvania are also included, via that per-district-subsection
fallback (app.ingestion.house_scraper._parse_district_results_by_section)
rather than the clean-table path -- confirmed by hand against NY-01's actual
vote totals before trusting it for all 26 districts, and against
Pennsylvania's own page having no "redistrict" mention at all (see
scripts/backfill_house_elections_2022.py) before trusting it too.

Iowa is included via the clean-table path (like Georgia/Michigan/etc.) --
confirmed via fetch_redistricting_changes returning no entry for Iowa, so
its 4 districts have used the same lines across 2022/2024/2026.

The remaining 31 states below were added after fetch_state_house_results
was extended to handle a few more page shapes it previously choked on: (1)
at-large states (Alaska, Delaware, North Dakota, South Dakota, Vermont,
Wyoming) use a singular "...election in {state}" title, not the plural
"...elections in {state}" every numbered-district state uses, and have no
"District N" subsections to fall back on either -- both now handled by a
dedicated at-large parser (Alaska itself is still excluded: its results
table is ranked-choice, a shape too different to safely reuse this parser
on); (2) some states' per-district tables use a trailing "±%" swing column
after "%" that the column-position logic used to read from the right,
silently misaligning every field on tables that have it (Maryland,
California); (3) North Dakota's Democratic candidates run under the
state's real "Democratic-NPL" party label, which needed normalizing to
"Democratic" the same way Minnesota's "DFL" already is; (4) Connecticut's
own table attaches a bare, non-bracketed "*" citation marker straight
after some districts' vote counts, which broke the numeric-only regex and
silently dropped 3 of its 5 districts.

All 9 states with new 2026 map lines (per fetch_redistricting_changes:
Alabama, Florida, Louisiana, Missouri, North Carolina, Ohio, Tennessee,
Texas, Utah) are deliberately EXCLUDED even though several of them do
parse cleanly now -- their 2024 Wikipedia district numbers don't
necessarily correspond to the current 2026 registry, same reasoning as
Georgia's exclusion. Alabama also already has hand-verified entries for
5 of its 7 districts (see AL-2 above) that a blind bulk pass shouldn't
risk touching regardless. California (no per-district "General election"
section published on this page at all -- only a primary-round table,
since it's a top-two state) and Alaska (ranked-choice) remain the only
two states this scraper still can't parse at all.

Only 2024 (not 2022) is used here: several states redrew their maps
between 2022 and 2024 independent of the 2026 redistricting fights
already tracked in app.ingestion.house_scraper.fetch_redistricting_changes,
so trusting 2022's district numbering at 50-state scale isn't safe
without individual per-state verification -- see
scripts/backfill_house_elections_2022.py, which adds 2022 only for the
subset of these states confirmed stable since 2022.

This only ever fills in a district whose `house_elections` is CURRENTLY an
empty list `[]` in the source file -- it will never overwrite Alabama's or
Alaska's hand-verified entries, or anything else already populated. Applied
via targeted line substitution (not a full file regenerate), so every
existing comment and entry not touched by this run is preserved byte for
byte.

Usage (from inside the backend container or a matching venv):
    python -m scripts.backfill_house_elections
"""

import logging
import re
from pathlib import Path

from app.ingestion.house_scraper import STATE_POSTAL_CODES, fetch_state_house_results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YEAR = 2024

# Confirmed by hand to publish a single clean per-district summary table
# (Georgia, Michigan, Minnesota, New Mexico, Connecticut, Iowa) or, for New
# York, a per-district-subsection page the fallback parser handles -- see
# module docstring. Every other state either lacks a parseable shape
# entirely, or enacted new 2026 district lines (see
# fetch_redistricting_changes) and is excluded regardless of table shape,
# since 2024's results wouldn't correspond to the current district registry.
ELIGIBLE_STATES = [
    "Georgia", "Michigan", "Minnesota", "New Mexico", "Connecticut", "New York", "Pennsylvania", "Iowa",
    # See module docstring for what changed in fetch_state_house_results to
    # make these 31 parseable, and why Alabama/Florida/Louisiana/Missouri/
    # North Carolina/Ohio/Tennessee/Texas/Utah (2026 redraw) and California/
    # Alaska (still unparseable) are deliberately left out.
    "Arizona", "Arkansas", "Colorado", "Delaware", "Hawaii", "Idaho", "Illinois", "Indiana",
    "Kansas", "Kentucky", "Maine", "Maryland", "Massachusetts", "Mississippi", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "North Dakota", "Oklahoma", "Oregon",
    "Rhode Island", "South Carolina", "South Dakota", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DISTRICT_FUNDAMENTALS_PATH = _REPO_ROOT / "app" / "data" / "district_fundamentals_data.py"

_KEY_RE = re.compile(r'^\s*"([a-z]{2}\d{2})":\s*\{\s*$')
_EMPTY_HOUSE_ELECTIONS_RE = re.compile(r'^(\s*)"house_elections":\s*\[\],\s*$')


def _district_key(state_code: str, district: int) -> str:
    return f"{state_code}{district:02d}"


def main(year: int = YEAR, states: list[str] = ELIGIBLE_STATES) -> None:
    to_fill: dict[str, list[dict]] = {}
    for state_name in states:
        state_code = STATE_POSTAL_CODES[state_name]
        results = fetch_state_house_results(state_name, year)
        if not results:
            logger.warning("no summary table found for %s %d -- skipped", state_name, year)
            continue
        for district, result in results.items():
            key = _district_key(state_code, district)
            to_fill[key] = [
                {
                    "year": year,
                    "dem_share": result.dem_share,
                    "incumbent_party": result.winner_party,
                }
            ]
        logger.info("%s: parsed %d districts", state_name, len(results))

    if not to_fill:
        logger.warning("nothing parsed -- file left unchanged")
        return

    lines = _DISTRICT_FUNDAMENTALS_PATH.read_text().splitlines(keepends=True)
    current_key: str | None = None
    n_filled = 0
    out_lines: list[str] = []
    for line in lines:
        key_match = _KEY_RE.match(line)
        if key_match:
            current_key = key_match.group(1)
            out_lines.append(line)
            continue

        empty_match = _EMPTY_HOUSE_ELECTIONS_RE.match(line)
        if empty_match and current_key in to_fill:
            indent = empty_match.group(1)
            entries = to_fill[current_key]
            out_lines.append(f'{indent}"house_elections": [\n')
            for e in entries:
                out_lines.append(
                    f'{indent}    {{"year": {e["year"]}, "dem_share": {e["dem_share"]!r}, '
                    f'"incumbent_party": {e["incumbent_party"]!r}}},\n'
                )
            out_lines.append(f"{indent}],\n")
            n_filled += 1
            continue

        out_lines.append(line)

    _DISTRICT_FUNDAMENTALS_PATH.write_text("".join(out_lines))
    logger.info(
        "backfilled house_elections for %d/%d parsed districts (rest already had data, or weren't in "
        "DISTRICT_FUNDAMENTALS under the expected key)",
        n_filled, len(to_fill),
    )


if __name__ == "__main__":
    main()
