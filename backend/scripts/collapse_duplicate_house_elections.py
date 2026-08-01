"""Collapses duplicate-year `house_elections` entries in
app/data/district_fundamentals_data.py down to one -- fallout from
backfill_house_elections_2022.py previously having no idempotency guard
(fixed now, see that script) and being rerun on districts that already
had a 2022 entry.

Only ever collapses a run of same-year entries when every copy is
byte-identical (same dem_share, same incumbent_party) -- that's a pure
duplicate with no judgment call involved. A district where the
duplicates actually disagree (seen for several Michigan districts, e.g.
38.40 vs 38.42) is left completely untouched and its key is printed to
the terminal instead, since picking between conflicting values is a
human call, not something this script should guess at.

Usage: python -m scripts.collapse_duplicate_house_elections
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DISTRICT_FUNDAMENTALS_PATH = _REPO_ROOT / "app" / "data" / "district_fundamentals_data.py"

_KEY_RE = re.compile(r'^\s*"([a-z]{2}\d{2})":\s*\{\s*$')
_ENTRY_RE = re.compile(
    r'^\s*\{"year":\s*(\d+),\s*"dem_share":\s*([\d.]+),\s*'
    r'"incumbent_party":\s*(\'[^\']*\'|"[^"]*"|None)\},\s*$'
)
_LIST_END_RE = re.compile(r'^\s*\],\s*$')


def main() -> None:
    lines = _DISTRICT_FUNDAMENTALS_PATH.read_text().splitlines(keepends=True)

    out_lines: list[str] = []
    current_key: str | None = None
    # Buffered entry lines for the house_elections list currently open --
    # held back (not appended to out_lines yet) until the matching "],"
    # is reached, so duplicates can be dropped before the list closes.
    pending_entries: list[tuple[str, str, str, str]] = []  # (line, year, dem_share, party)
    in_list = False
    n_collapsed_districts = 0
    n_lines_dropped = 0
    conflicts: list[str] = []

    for line in lines:
        key_match = _KEY_RE.match(line)
        if key_match:
            current_key = key_match.group(1)
            out_lines.append(line)
            continue

        if in_list:
            entry_match = _ENTRY_RE.match(line)
            if entry_match:
                year, dem_share, party = entry_match.groups()
                pending_entries.append((line, year, dem_share, party))
                continue

            if _LIST_END_RE.match(line):
                seen: dict[str, tuple[str, str]] = {}
                has_conflict = False
                for _, year, dem_share, party in pending_entries:
                    if year in seen and seen[year] != (dem_share, party):
                        has_conflict = True
                    seen.setdefault(year, (dem_share, party))
                if has_conflict:
                    conflicts.append(current_key)
                    out_lines.extend(l for l, _, _, _ in pending_entries)
                else:
                    emitted_years: set[str] = set()
                    collapsed_any = False
                    for entry_line, year, _, _ in pending_entries:
                        if year in emitted_years:
                            collapsed_any = True
                            n_lines_dropped += 1
                            continue
                        emitted_years.add(year)
                        out_lines.append(entry_line)
                    if collapsed_any:
                        n_collapsed_districts += 1

                pending_entries = []
                in_list = False
                out_lines.append(line)
                continue

        if line.rstrip().endswith('"house_elections": ['):
            in_list = True
            pending_entries = []
            out_lines.append(line)
            continue

        out_lines.append(line)

    _DISTRICT_FUNDAMENTALS_PATH.write_text("".join(out_lines))
    print(f"collapsed {n_collapsed_districts} district(s), dropped {n_lines_dropped} duplicate line(s)")
    if conflicts:
        print(f"{len(conflicts)} district(s) had CONFLICTING values -- left untouched: {', '.join(sorted(conflicts))}")


if __name__ == "__main__":
    main()
