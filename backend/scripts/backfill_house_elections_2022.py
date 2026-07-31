"""Adds real 2022 `house_elections` entries alongside the 2024 ones already
backfilled by scripts/backfill_house_elections.py, for the states confirmed
to have had NO mid-decade congressional redraw between 2022 and 2024 --
unlike Georgia (2023 court-ordered map, Alpha Phi Alpha v. Raffensperger)
and Alabama (2023 VRA remedy), whose 2022 results sit on now-obsolete
district lines and are excluded here for the same reason AL's 2022 data
required individual per-district judgment rather than a blind bulk merge.

Confirmed via each state's own 2024 Wikipedia elections page (no
"redistrict" mention at all) to have used the same district lines
continuously since the 2020 census cycle: Michigan, Minnesota, New Mexico,
Connecticut.

New York is a partial case rather than all-or-nothing: its own "2024 United
States House of Representatives elections in New York" page states the
February 2024 map only changed the 1st, 3rd, 18th, and 22nd districts
("resulting in the 3rd, 18th, and 22nd congressional districts becoming
more Democratic, while the 1st became more Republican") -- the other 22
districts kept their 2022 (special-master-map) lines. EXCLUDED_DISTRICTS
skips just those four for New York, the same individual-judgment principle
as Alabama's AL-2 (there, hand-curated with a comment instead of an
automated skip, since AL-2 kept a 2024 entry anyway; here the whole point
of this script is the *2022* entry, so the four affected districts simply
don't get one).

Only ever appends a 2022 entry to a district whose house_elections
currently contains exactly the one 2024 entry from the prior backfill --
never touches Georgia, Alabama/Alaska, or anything else.

Usage: python -m scripts.backfill_house_elections_2022
"""

import logging
import re
from pathlib import Path

from app.ingestion.house_scraper import STATE_POSTAL_CODES, fetch_state_house_results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YEAR = 2022

# Confirmed stable (no mid-decade redraw) -- see module docstring. Georgia
# is deliberately NOT included here even though it got a 2024 entry from
# the prior backfill, since its map changed between 2022 and 2024.
ELIGIBLE_STATES = ["Michigan", "Minnesota", "New Mexico", "Connecticut", "New York"]

# Per-state district numbers to skip even though the state itself is
# otherwise eligible -- see New York's note in the module docstring.
EXCLUDED_DISTRICTS: dict[str, set[int]] = {
    "New York": {1, 3, 18, 22},
}

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DISTRICT_FUNDAMENTALS_PATH = _REPO_ROOT / "app" / "data" / "district_fundamentals_data.py"

_KEY_RE = re.compile(r'^\s*"([a-z]{2}\d{2})":\s*\{\s*$')
_2024_ENTRY_RE = re.compile(r'^(\s*)\{"year": 2024, "dem_share":.*\},\s*$')


def _district_key(state_code: str, district: int) -> str:
    return f"{state_code}{district:02d}"


def main() -> None:
    to_add: dict[str, dict] = {}
    for state_name in ELIGIBLE_STATES:
        state_code = STATE_POSTAL_CODES[state_name]
        excluded = EXCLUDED_DISTRICTS.get(state_name, set())
        results = fetch_state_house_results(state_name, YEAR)
        if not results:
            logger.warning("no summary table found for %s %d -- skipped", state_name, YEAR)
            continue
        n_skipped = 0
        for district, result in results.items():
            if district in excluded:
                n_skipped += 1
                continue
            key = _district_key(state_code, district)
            to_add[key] = {
                "year": YEAR,
                "dem_share": result.dem_share,
                "incumbent_party": result.winner_party,
            }
        logger.info(
            "%s: parsed %d districts (%d skipped, redrawn since %d)",
            state_name, len(results) - n_skipped, n_skipped, YEAR,
        )

    if not to_add:
        logger.warning("nothing parsed -- file left unchanged")
        return

    lines = _DISTRICT_FUNDAMENTALS_PATH.read_text().splitlines(keepends=True)
    current_key: str | None = None
    n_added = 0
    out_lines: list[str] = []
    for line in lines:
        key_match = _KEY_RE.match(line)
        if key_match:
            current_key = key_match.group(1)
            out_lines.append(line)
            continue

        entry_match = _2024_ENTRY_RE.match(line)
        if entry_match and current_key in to_add:
            indent = entry_match.group(1)
            e = to_add[current_key]
            out_lines.append(
                f'{indent}{{"year": {e["year"]}, "dem_share": {e["dem_share"]!r}, '
                f'"incumbent_party": {e["incumbent_party"]!r}}},\n'
            )
            n_added += 1
            current_key = None  # only ever insert once per district
            out_lines.append(line)
            continue

        out_lines.append(line)

    _DISTRICT_FUNDAMENTALS_PATH.write_text("".join(out_lines))
    logger.info("added a 2022 house_elections entry to %d/%d parsed districts", n_added, len(to_add))


if __name__ == "__main__":
    main()
