"""Re-fetches the single "2026 United States House of Representatives
elections" Wikipedia page (see app.ingestion.house_scraper) and fills in
real candidates for districts that were left with fewer than 2 confirmed
candidates by the original bulk generation
(scripts/generate_house_seed_data.py) or a prior run of this script --
i.e. districts whose primary hadn't settled at scrape time.

Unlike scripts/generate_house_seed_data.py, this is safe to re-run
repeatedly and does NOT touch any district that already has a full
2-candidate field -- so any hand-added real name, "Nominee (TBD)"
placeholder, photo_url, or kalshi_ticker (e.g. Alabama's districts) is
left completely untouched. Only genuinely bare/partial districts get
overwritten, using the same candidate-building logic as the original
generator (house_scraper._settled_general_field /
generate_house_seed_data._build_candidates), so a still-unsettled
same-party primary continues to be left out rather than guessed at.

Usage: python -m scripts.refresh_house_candidates
"""

import logging
import re
from pathlib import Path

from app.ingestion.house_scraper import fetch_all_districts
from app.seed.house_seed_data import HOUSE_RACES
from scripts.generate_house_seed_data import _build_candidates, _district_key, _format_candidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOUSE_SEED_PATH = _REPO_ROOT / "app" / "seed" / "house_seed_data.py"

_KEY_RE = re.compile(r'^\s*"([a-z]{2}\d{2})":\s*\{\s*$')
_CANDIDATES_START_RE = re.compile(r'^(\s*)"candidates":\s*\[\s*$')
_CANDIDATES_END_RE = re.compile(r'^(\s*)\],\s*$')


def main() -> None:
    logger.info("fetching current House district data from Wikipedia...")
    districts = fetch_all_districts()
    if not districts:
        logger.warning("scrape returned no districts -- file left unchanged")
        return

    to_update: dict[str, list[dict]] = {}
    for d in districts:
        key = _district_key(d.state_code, d.district)
        existing = HOUSE_RACES.get(key)
        if existing is None:
            continue  # a district not in the current registry at all -- out of scope for a refresh
        current_count = len(existing["candidates"])
        if current_count >= 2:
            continue  # already full (hand-edited or previously settled) -- never touched
        fresh = _build_candidates(d)
        if len(fresh) > current_count:
            to_update[key] = fresh

    if not to_update:
        logger.info("no under-filled districts newly resolved -- file left unchanged")
        return

    lines = _HOUSE_SEED_PATH.read_text().splitlines(keepends=True)
    current_key: str | None = None
    in_target_candidates_block = False
    n_updated = 0
    out_lines: list[str] = []
    for line in lines:
        key_match = _KEY_RE.match(line)
        if key_match:
            current_key = key_match.group(1)
            out_lines.append(line)
            continue

        start_match = _CANDIDATES_START_RE.match(line)
        if start_match and current_key in to_update and not in_target_candidates_block:
            indent = start_match.group(1)
            out_lines.append(line)
            for c in to_update[current_key]:
                out_lines.append(_format_candidate(c, indent + "    ") + "\n")
            in_target_candidates_block = True
            n_updated += 1
            continue

        if in_target_candidates_block:
            if _CANDIDATES_END_RE.match(line):
                in_target_candidates_block = False
                out_lines.append(line)
            # drop every original candidate-dict line inside the block being replaced
            continue

        out_lines.append(line)

    _HOUSE_SEED_PATH.write_text("".join(out_lines))
    logger.info(
        "updated candidates for %d/%d districts that had newly-settled data (%d still under-filled)",
        n_updated, len(to_update), sum(1 for r in HOUSE_RACES.values() if len(r["candidates"]) < 2) - n_updated,
    )


if __name__ == "__main__":
    main()
