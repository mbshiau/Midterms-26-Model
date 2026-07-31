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

Only 2024 (not 2022) is used: several states redrew their maps between
2022 and 2024 independent of the 2026 redistricting fights already tracked
in app.ingestion.house_scraper.fetch_redistricting_changes, so trusting
2022's district numbering at all 50-state scale isn't safe without
individual verification (same lesson as Alabama's AL-2, done by hand).

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
# (Georgia, Michigan, Minnesota, New Mexico, Connecticut) or, for New York,
# a per-district-subsection page the fallback parser handles -- see module
# docstring. Every other state either lacks a parseable shape entirely, or
# enacted new 2026 district lines (see fetch_redistricting_changes) and is
# excluded regardless of table shape, since 2024's results wouldn't
# correspond to the current district registry.
ELIGIBLE_STATES = ["Georgia", "Michigan", "Minnesota", "New Mexico", "Connecticut", "New York", "Pennsylvania"]

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
