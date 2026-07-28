"""Fills in a real kalshi_ticker for HOUSE_RACES candidates that don't have
one yet, by querying Kalshi's own market listing for that district
(app.ingestion.kalshi_scraper.fetch_house_race_markets, filtered by
event_ticker=KXHOUSERACE-{STATE}{DD}-26) rather than guessing the ticker
string from a naming pattern -- confirmed against real Kalshi data that a
standard 2-candidate race lists one market per party (yes_sub_title
"Republican party" / "Democratic party"), while a race with a real
third-party/independent candidate instead lists one market per named
candidate.

Requires real Kalshi API credentials (settings.kalshi_api_key_id /
kalshi_private_key_path) -- run this from inside the backend container,
where the secret is mounted; returns immediately with nothing done if
they're not configured (same fail-soft convention as kalshi_scraper's
other functions).

Never guesses: a candidate who can't be confidently matched to exactly one
of that district's real Kalshi markets (by party, or by name for a
named-candidate market) keeps kalshi_ticker: None. Only ever touches a
candidate line whose kalshi_ticker is CURRENTLY None -- Alabama's
hand-added tickers are left untouched.

A party-keyed market ("Democratic party") is only trusted when exactly one
candidate in that race has that party -- a real California/Washington
jungle-primary race can send two same-party candidates to the general, and
Kalshi's own market can't distinguish between them, so blindly assigning
that ticker to both would silently show the same ticker on two different
people (caught by hand across 8 CA districts, see conversation on
2026-07-27). Those races are simply left without a ticker rather than
guessing.

Usage (inside the backend container): python -m scripts.backfill_kalshi_tickers
"""

import ast
import logging
import re
import time
from pathlib import Path

from app.ingestion.kalshi_scraper import fetch_house_race_markets
from app.seed.house_seed_data import HOUSE_RACES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOUSE_SEED_PATH = _REPO_ROOT / "app" / "seed" / "house_seed_data.py"

_KEY_RE = re.compile(r'^\s*"([a-z]{2}\d{2})":\s*\{\s*$')
_CANDIDATE_LINE_RE = re.compile(r'^(\s*)(\{"name":.*\}),\s*$')


def _ticker_lookup(markets) -> tuple[dict[str, str], dict[str, str]]:
    """(by_party, by_name) ticker maps for one district's real markets."""
    by_party: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for m in markets:
        sub_title = m.yes_sub_title or ""
        if sub_title.endswith(" party"):
            by_party[sub_title.removesuffix(" party")] = m.ticker
        else:
            by_name[sub_title] = m.ticker
    return by_party, by_name


def main() -> None:
    lines = _HOUSE_SEED_PATH.read_text().splitlines(keepends=True)
    current_key: str | None = None
    by_party: dict[str, str] = {}
    by_name: dict[str, str] = {}
    fetched_keys: set[str] = set()
    out_lines: list[str] = []
    n_filled = 0
    n_checked = 0

    for line in lines:
        key_match = _KEY_RE.match(line)
        if key_match:
            current_key = key_match.group(1)
            out_lines.append(line)
            continue

        candidate_match = _CANDIDATE_LINE_RE.match(line)
        if not candidate_match or current_key is None:
            out_lines.append(line)
            continue

        indent, dict_text = candidate_match.groups()
        try:
            candidate = ast.literal_eval(dict_text)
        except (ValueError, SyntaxError):
            out_lines.append(line)
            continue

        if candidate.get("kalshi_ticker") is not None:
            out_lines.append(line)
            continue

        if current_key not in fetched_keys:
            state_code, district = current_key[:2], int(current_key[2:])
            markets = fetch_house_race_markets(state_code, district)
            time.sleep(0.15)
            by_party, by_name = _ticker_lookup(markets) if markets else ({}, {})
            fetched_keys.add(current_key)

        n_checked += 1
        # Kalshi's "Democratic party"/"Republican party" market is a single
        # per-party outcome -- meaningless to assign to a specific candidate
        # when 2+ candidates in this race share that party (e.g. a real
        # California/Washington jungle-primary top-two-same-party general),
        # since it can't actually distinguish between them. Only trust the
        # party-keyed ticker when this race has exactly one candidate of
        # that party; a named per-candidate market (by_name) is always
        # unambiguous and safe to use regardless.
        race_candidates = HOUSE_RACES.get(current_key, {}).get("candidates", [])
        same_party_count = sum(1 for c in race_candidates if c.get("party") == candidate.get("party"))
        party_ticker = by_party.get(candidate.get("party")) if same_party_count <= 1 else None
        ticker = party_ticker or by_name.get(candidate.get("name"))
        if ticker is None:
            out_lines.append(line)
            continue

        candidate["kalshi_ticker"] = ticker
        out_lines.append(
            f'{indent}{{"name": {candidate["name"]!r}, "party": {candidate["party"]!r}, '
            f'"incumbent": {candidate["incumbent"]!r}, "photo_url": {candidate["photo_url"]!r}, '
            f'"kalshi_ticker": {candidate["kalshi_ticker"]!r}}},\n'
        )
        n_filled += 1

    _HOUSE_SEED_PATH.write_text("".join(out_lines))
    logger.info(
        "filled kalshi_ticker for %d/%d candidates in %d districts with a live Kalshi market",
        n_filled, n_checked, len(fetched_keys),
    )


if __name__ == "__main__":
    main()
