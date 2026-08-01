"""Scans app/data/district_fundamentals_data.py for any district whose
`house_elections` list has more than one entry for the same year --
this should never happen (each district gets at most one real result per
election year), but backfill_house_elections_2022.py used to have no
idempotency guard and would silently append a duplicate every time it was
rerun on a district that already had one (fixed now, but the damage from
past runs is still sitting in the file).

Deliberately does NOT try to auto-resolve which duplicate value is
correct -- some of the duplicates found aren't even byte-identical (e.g.
a district with both 38.40 and 38.42 for the same year), which means a
naive "keep one" pick could silently commit to the wrong number. Instead
this only ever reports; a human decides what the real value is (or
reruns the district through the scraper by hand) and edits the file
directly.

Usage: python -m scripts.check_house_elections_duplicates
"""

import re
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DISTRICT_FUNDAMENTALS_PATH = _REPO_ROOT / "app" / "data" / "district_fundamentals_data.py"

_BLOCK_RE = re.compile(r'"([a-z]{2}\d{2})":\s*\{[^}]*?"house_elections":\s*\[(.*?)\]', re.S)
_ENTRY_RE = re.compile(r'\{"year":\s*(\d+),\s*"dem_share":\s*([\d.]+),\s*"incumbent_party":\s*\'(\w+)\'\}')


def main() -> None:
    text = _DISTRICT_FUNDAMENTALS_PATH.read_text()
    found = False
    for district_key, body in _BLOCK_RE.findall(text):
        entries = _ENTRY_RE.findall(body)
        years = Counter(year for year, _, _ in entries)
        dupe_years = [year for year, count in years.items() if count > 1]
        if not dupe_years:
            continue
        found = True
        for year in dupe_years:
            values = [(dem_share, party) for y, dem_share, party in entries if y == year]
            print(f"{district_key}: {len(values)}x entries for {year} -- {values}")

    if not found:
        print("no duplicate-year house_elections entries found")


if __name__ == "__main__":
    main()
