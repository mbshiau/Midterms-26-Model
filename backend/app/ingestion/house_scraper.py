"""Live House-race fetcher: pulls the "2026 United States House of
Representatives elections" summary page from Wikipedia and parses it into
per-district records for the bulk seed (see
backend/scripts/generate_house_seed_data.py).

Same conventions as app.ingestion.wikipedia_scraper (reused directly for
the actual HTTP fetch): MediaWiki API, not scraped rendered HTML, real
User-Agent, never fabricates a row it can't confidently parse -- an
ambiguous row is skipped and logged rather than guessed at.

That one page turns out to carry everything needed for the bulk
candidate/incumbency seed in a single fetch: a per-state "District |
Incumbent | Candidates" table for all 50 states (member name, party, 2025
Cook PVI, and a "Status" column -- "Incumbent renominated" /"Incumbent
retiring" / "None (new seat)" / etc. -- that already reflects each state's
*current*, post-2025-26-redistricting district numbering), plus a
"Mid-decade redistricting changes" table naming which states enacted new
maps. So unlike the original plan sketch, there's no need to separately
fetch the national member roster or 50 individual state subpages -- this
module only ever makes one HTTP request per generator run.
"""

import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from app.ingestion.wikipedia_scraper import fetch_wikipedia_html

logger = logging.getLogger(__name__)

HOUSE_ELECTIONS_PAGE_TITLE = "2026_United_States_House_of_Representatives_elections"

STATE_POSTAL_CODES = {
    "Alabama": "al", "Alaska": "ak", "Arizona": "az", "Arkansas": "ar", "California": "ca",
    "Colorado": "co", "Connecticut": "ct", "Delaware": "de", "Florida": "fl", "Georgia": "ga",
    "Hawaii": "hi", "Idaho": "id", "Illinois": "il", "Indiana": "in", "Iowa": "ia",
    "Kansas": "ks", "Kentucky": "ky", "Louisiana": "la", "Maine": "me", "Maryland": "md",
    "Massachusetts": "ma", "Michigan": "mi", "Minnesota": "mn", "Mississippi": "ms", "Missouri": "mo",
    "Montana": "mt", "Nebraska": "ne", "Nevada": "nv", "New Hampshire": "nh", "New Jersey": "nj",
    "New Mexico": "nm", "New York": "ny", "North Carolina": "nc", "North Dakota": "nd", "Ohio": "oh",
    "Oklahoma": "ok", "Oregon": "or", "Pennsylvania": "pa", "Rhode Island": "ri", "South Carolina": "sc",
    "South Dakota": "sd", "Tennessee": "tn", "Texas": "tx", "Utah": "ut", "Vermont": "vt",
    "Virginia": "va", "Washington": "wa", "West Virginia": "wv", "Wisconsin": "wi", "Wyoming": "wy",
}

# States with a genuine nonpartisan blanket ("jungle") primary, where the
# top two finishers advance to the general regardless of party -- a
# same-party November matchup (e.g. two Democrats) is a real, settled
# result there, not an unresolved same-party primary the way it would be
# in a closed/open-primary state. Only these two currently use that system
# for U.S. House races.
_JUNGLE_PRIMARY_STATES = {"California", "Washington"}

_BULLET = "▌"
_FOOTNOTE_RE = re.compile(r"\[\s*[^\[\]]*?\s*\]")
_REDISTRICTED_SUFFIX_RE = re.compile(r"\s*Redistricted from the .*district.*$", re.IGNORECASE)
_CANDIDATE_RE = re.compile(r"^(.*?)\s*\(([A-Za-z][A-Za-z\s]*)\)")


@dataclass
class ScrapedCandidate:
    name: str
    party: str


@dataclass
class ScrapedDistrict:
    state_code: str
    state_name: str
    district: int  # 1+ ; at-large states use 1
    incumbent_name: str | None
    incumbent_party: str | None
    is_open_seat: bool
    status: str
    # Raw 2025 Cook PVI citation as printed on the page (e.g. "R+7") -- parsed
    # into a signed dem-margin point value by
    # scripts.generate_house_seed_data._parse_pvi_dem_margin and used
    # directly as DISTRICT_FUNDAMENTALS[key]["pvi_dem_margin_pts"] (see
    # app.services.fundamentals.district_lean). Kept as a raw string here
    # since this module only parses the page, not the domain meaning of PVI.
    pvi: str | None
    # The settled two-party general-election field where confidently
    # parseable (see _parse_candidates_cell) -- may hold 0, 1, or 2
    # candidates; never guessed beyond what the page actually lists.
    candidates: list[ScrapedCandidate] = field(default_factory=list)
    wikipedia_page_title: str = HOUSE_ELECTIONS_PAGE_TITLE


@dataclass
class RedistrictingStatus:
    state_name: str
    status: str  # "New districts enacted" | "Districts left in place" | ...
    notes: str


def _clean_footnotes(text: str) -> str:
    # Also strips stray soft hyphens (U+00AD) -- Wikipedia inserts these
    # inside some words (e.g. "Vac\xadant") as invisible line-break hints,
    # which would otherwise silently break exact-string checks like
    # `.startswith("vacant")` below.
    return _FOOTNOTE_RE.sub("", text).replace("\xad", "").strip()


def _parse_candidates_cell(text: str) -> list[ScrapedCandidate]:
    """Splits a "▌ Name (Party) ...  ▌ Name (Party) ..." cell into
    candidates. Real vote-share percentages/footnotes trailing a name are
    simply outside the regex match and dropped -- only name+party are
    trusted from this cell."""
    candidates = []
    for token in _clean_footnotes(text).split(_BULLET):
        token = token.strip()
        if not token:
            continue
        match = _CANDIDATE_RE.match(token)
        if not match:
            continue
        candidates.append(ScrapedCandidate(name=match.group(1).strip(), party=match.group(2).strip()))
    return candidates


def _settled_general_field(candidates: list[ScrapedCandidate], state_name: str) -> list[ScrapedCandidate]:
    """Reduces a district's full candidate list (which can include third
    parties and, for a district whose primary hasn't resolved yet, several
    same-party primary contenders) down to a real general-election matchup.

    In a California/Washington jungle primary, a same-party November
    matchup is a real settled result (not an unresolved primary) -- so
    when the page has already narrowed the field to 2 or fewer names there,
    that field is trusted as-is regardless of party. Everywhere else, only
    each major party's *exactly one* listed candidate is trusted; more than
    one same-party candidate means that party's primary isn't settled in
    this data yet, so that party's slot is left out entirely rather than
    guessing which contender will win -- same real-data-only convention as
    every other seed entry in this project."""
    if state_name in _JUNGLE_PRIMARY_STATES and len(candidates) <= 2:
        return candidates

    by_party: dict[str, list[ScrapedCandidate]] = {}
    for c in candidates:
        by_party.setdefault(c.party, []).append(c)

    settled = []
    for party in ("Democratic", "Republican"):
        matches = by_party.get(party, [])
        if len(matches) == 1:
            settled.append(matches[0])
    return settled


def iter_state_tables(soup: BeautifulSoup):
    """Yields (state_name, table) for each of the 50 states' own
    District/Incumbent/Candidates wikitable on the main elections page --
    identified by each table's nearest preceding heading being a
    recognized state name, not a fixed table index (so this stays correct
    if the page's section order or unrelated table count ever changes)."""
    for table in soup.find_all("table", class_="wikitable"):
        heading = next(
            (el.get_text(strip=True) for el in table.find_all_previous(["h2", "h3", "h4"])), None
        )
        if heading in STATE_POSTAL_CODES:
            yield heading, table


def parse_state_table(state_name: str, table: Tag) -> list[ScrapedDistrict]:
    state_code = STATE_POSTAL_CODES[state_name]
    rows = table.find_all("tr")

    header_row = None
    for row in rows[:3]:
        texts = [c.get_text(" ", strip=True).lower() for c in row.find_all(["th", "td"])]
        if "member" in texts and "party" in texts:
            header_row = texts
            break
    if header_row is None:
        logger.warning("house_scraper: no per-district header row found for %s", state_name)
        return []

    def col(name: str) -> int | None:
        return next((i for i, h in enumerate(header_row) if name in h), None)

    pvi_idx = col("pvi")
    member_idx = col("member")
    party_idx = col("party")
    status_idx = col("status")

    district_pattern = re.compile(rf"^{re.escape(state_name)} (\d+|at-large)$")

    districts: list[ScrapedDistrict] = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        first_text = cells[0].get_text(" ", strip=True).replace("\xa0", " ")
        match = district_pattern.match(first_text)
        if not match:
            # Either a header row, or a rowspan continuation row (a second
            # incumbent redistricted into this same seat, e.g. a
            # multi-incumbent redraw) -- skipped rather than guessed at;
            # the district is still seeded from its own primary row below.
            continue
        district = 1 if match.group(1) == "at-large" else int(match.group(1))

        def cell_text(idx: int | None) -> str:
            return _clean_footnotes(cells[idx].get_text(" ", strip=True)) if idx is not None and idx < len(cells) else ""

        pvi = cell_text(pvi_idx) or None
        raw_member = cell_text(member_idx)
        member_name = _REDISTRICTED_SUFFIX_RE.sub("", raw_member).strip()
        party = cell_text(party_idx) or None
        status = cell_text(status_idx)
        # A currently-vacant seat awaiting a special election ("Vacant") is
        # functionally open for seeding purposes, same as a genuine new/open
        # seat ("None (new seat)") -- neither has a real sitting incumbent
        # to seed as a candidate.
        member_lower = member_name.lower()
        is_open_seat = not member_name or member_lower.startswith("none") or member_lower.startswith("vacant")

        candidates_cell = cells[-1].get_text(" ", strip=True)
        all_candidates = _parse_candidates_cell(candidates_cell)

        districts.append(
            ScrapedDistrict(
                state_code=state_code,
                state_name=state_name,
                district=district,
                incumbent_name=None if is_open_seat else member_name,
                incumbent_party=None if is_open_seat else party,
                is_open_seat=is_open_seat,
                status=status,
                pvi=pvi,
                candidates=_settled_general_field(all_candidates, state_name),
            )
        )

    return districts


def fetch_all_districts() -> list[ScrapedDistrict]:
    """Fetches and parses every state's district table. Returns [] (rather
    than raising) if the page can't be fetched at all, same fail-soft
    convention as app.ingestion.wikipedia_scraper.fetch_general_election_polls
    -- a scheduled/manual re-run should never crash on a transient network
    error."""
    html = fetch_wikipedia_html(HOUSE_ELECTIONS_PAGE_TITLE)
    if html is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    districts: list[ScrapedDistrict] = []
    for state_name, table in iter_state_tables(soup):
        districts.extend(parse_state_table(state_name, table))
    return districts


def fetch_redistricting_changes() -> dict[str, RedistrictingStatus]:
    """Parses the "Mid-decade redistricting changes" summary table --
    which states enacted a genuinely new map for 2026 (as opposed to
    litigation/proposals that left the existing map in place) -- keyed by
    state name. Used to flag those states' HOUSE_RACES entries with an
    inline comment (see backend/scripts/generate_house_seed_data.py)."""
    html = fetch_wikipedia_html(HOUSE_ELECTIONS_PAGE_TITLE)
    if html is None:
        return {}
    soup = BeautifulSoup(html, "html.parser")

    target_table = None
    for table in soup.find_all("table", class_="wikitable"):
        headers = [c.get_text(" ", strip=True).lower() for c in table.find("tr").find_all(["th", "td"])]
        if any("change in partisanship" in h for h in headers):
            target_table = table
            break
    if target_table is None:
        logger.warning("house_scraper: redistricting-changes table not found")
        return {}

    out: dict[str, RedistrictingStatus] = {}
    for row in target_table.find_all("tr")[2:]:  # skip the 2 header rows (main + D/C/R sub-header)
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        state_name = cells[0].get_text(" ", strip=True)
        if state_name not in STATE_POSTAL_CODES:
            continue  # the trailing "Net change (as of ...)" summary row
        status = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
        notes = _clean_footnotes(cells[2].get_text(" ", strip=True)) if len(cells) > 2 else ""
        out[state_name] = RedistrictingStatus(state_name=state_name, status=status, notes=notes)

    return out
