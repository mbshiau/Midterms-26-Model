"""Fills in a real photo_url for HOUSE_RACES candidates that don't have one
yet, using each candidate's own Wikipedia article -- captured as
wiki_page_title while parsing the main "2026 House elections" page (see
app.ingestion.house_scraper's _parse_candidates_cell/_wiki_page_title_for)
-- and MediaWiki's pageimages API (app.ingestion.wikipedia_scraper.
fetch_page_thumbnail), the same real infobox photo Wikipedia itself shows.

Never guesses: a candidate whose name isn't linked to their own article on
the source page (a longer-shot challenger without a Wikipedia page yet)
simply keeps photo_url: None, same real-data-only convention as everywhere
else. Only ever touches a candidate line whose photo_url is CURRENTLY None
-- any hand-added photo (e.g. Alabama's) is left untouched.

Usage: python -m scripts.backfill_candidate_photos
"""

import ast
import logging
import re
import time
from pathlib import Path

from app.ingestion.house_scraper import fetch_all_districts
from app.ingestion.wikipedia_scraper import fetch_page_thumbnail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOUSE_SEED_PATH = _REPO_ROOT / "app" / "seed" / "house_seed_data.py"

_CANDIDATE_LINE_RE = re.compile(r'^(\s*)(\{"name":.*\}),\s*$')


def _collect_wiki_page_titles() -> dict[str, str]:
    """name -> wiki_page_title, gathered from both each district's incumbent
    (Member column) and its Candidates cell -- a name appearing in both
    (the common case) just gets overwritten with the same value."""
    by_name: dict[str, str] = {}
    for d in fetch_all_districts():
        if d.incumbent_name and d.incumbent_wiki_page_title:
            by_name[d.incumbent_name] = d.incumbent_wiki_page_title
        for c in d.candidates:
            if c.wiki_page_title:
                by_name[c.name] = c.wiki_page_title
    return by_name


def main() -> None:
    logger.info("fetching current House district data from Wikipedia...")
    wiki_titles_by_name = _collect_wiki_page_titles()
    logger.info("found Wikipedia article links for %d candidate names", len(wiki_titles_by_name))

    lines = _HOUSE_SEED_PATH.read_text().splitlines(keepends=True)
    out_lines: list[str] = []
    photo_cache: dict[str, str | None] = {}
    n_filled = 0
    n_checked = 0

    for line in lines:
        match = _CANDIDATE_LINE_RE.match(line)
        if not match:
            out_lines.append(line)
            continue

        indent, dict_text = match.groups()
        try:
            candidate = ast.literal_eval(dict_text)
        except (ValueError, SyntaxError):
            out_lines.append(line)
            continue

        wiki_title = wiki_titles_by_name.get(candidate.get("name"))
        if candidate.get("photo_url") is not None or not wiki_title:
            out_lines.append(line)
            continue

        n_checked += 1
        if wiki_title not in photo_cache:
            photo_cache[wiki_title] = fetch_page_thumbnail(wiki_title)
            time.sleep(0.1)
        photo_url = photo_cache[wiki_title]

        if photo_url is None:
            out_lines.append(line)
            continue

        candidate["photo_url"] = photo_url
        out_lines.append(
            f'{indent}{{"name": {candidate["name"]!r}, "party": {candidate["party"]!r}, '
            f'"incumbent": {candidate["incumbent"]!r}, "photo_url": {candidate["photo_url"]!r}, '
            f'"kalshi_ticker": {candidate["kalshi_ticker"]!r}}},\n'
        )
        n_filled += 1

    _HOUSE_SEED_PATH.write_text("".join(out_lines))
    logger.info("filled photo_url for %d/%d candidates that had a linked Wikipedia article", n_filled, n_checked)


if __name__ == "__main__":
    main()
