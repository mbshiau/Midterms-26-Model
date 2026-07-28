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
from functools import lru_cache

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
    # This candidate's own Wikipedia article title (e.g. "Gary_Palmer"), read
    # directly from the "▌ Name (Party)" cell's real <a href="/wiki/..."> --
    # None when the page doesn't link that name to its own article (a
    # lesser-known challenger without a Wikipedia page yet). Used by
    # scripts/backfill_candidate_photos.py to fetch a real infobox photo via
    # MediaWiki's pageimages API -- never guessed at from just a name.
    wiki_page_title: str | None = None


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
    # Same as ScrapedCandidate.wiki_page_title, but for the incumbent's own
    # Member-column link -- kept separate since an incumbent's photo is
    # useful even for a district whose Candidates cell isn't settled yet.
    incumbent_wiki_page_title: str | None = None


@dataclass
class RedistrictingStatus:
    state_name: str
    status: str  # "New districts enacted" | "Districts left in place" | ...
    notes: str


@dataclass
class StateDistrictResult:
    district: int
    dem_share: float  # two-party (Dem votes / (Dem + Rep votes) * 100)
    winner_party: str | None  # first word of the page's own "Result" cell, e.g. "Republican" from "Republican hold"


_DISTRICT_ROW_RE = re.compile(r"^District (\d+)$|^At-large$")


def _row_cells(row: Tag) -> list[str]:
    return [_clean_footnotes(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]


def _parse_district_results_table(soup: BeautifulSoup) -> dict[int, StateDistrictResult] | None:
    """Looks for a single per-state "District | <Party> | <Party> | Total |
    Result" (or Ohio's flatter "District | Party #, Party %, ... | Elected")
    summary table and parses real two-party dem_share per district from it.

    Confirmed by hand to exist, in one of these two shapes, on only a
    minority of states' "20XX United States House of Representatives
    elections in {state}" pages (e.g. Georgia, Michigan, Minnesota, New
    Mexico) -- most other states spread results across many per-district
    subsections instead, which this intentionally does NOT attempt to parse
    (too state-specific to trust without individual verification per state,
    same real-data-only caution as everywhere else in this project). Returns
    None when no such table is found, rather than guessing at a
    lower-confidence shape."""
    for table in soup.find_all("table", class_="wikitable"):
        rows = table.find_all("tr")
        if not rows:
            continue
        data_start = None
        for i, row in enumerate(rows):
            cells = _row_cells(row)
            if cells and _DISTRICT_ROW_RE.match(cells[0]):
                data_start = i
                break
        if data_start is None or data_start == 0:
            continue

        header_rows = [_row_cells(r) for r in rows[:data_start]]
        top = header_rows[0]
        if top[0] != "District":
            continue
        groups = top[1:-1]  # party (+ "Total") labels, excludes "District" and "Result"/"Elected"
        if len(groups) < 2:
            continue

        sample = _row_cells(rows[data_start])
        expected_flat = 1 + len(groups) + 1  # District + 1 votes col/group (Ohio-style) + Result
        expected_nested = 1 + 2 * len(groups) + 1  # District + Votes/% pair/group (GA-style) + Result
        if len(header_rows) == 1 and len(sample) == expected_flat:
            step = 1
        elif len(sample) == expected_nested:
            step = 2
        else:
            continue  # a table shaped like this but not matching either layout -- skip rather than guess

        out: dict[int, StateDistrictResult] = {}
        for row in rows[data_start:]:
            cells = _row_cells(row)
            if not cells or not _DISTRICT_ROW_RE.match(cells[0]):
                continue
            district = 1 if cells[0] == "At-large" else int(cells[0].split()[1])
            votes: dict[str, int | None] = {}
            for i, group in enumerate(groups):
                idx = 1 + step * i
                if idx < len(cells):
                    raw = cells[idx].replace(",", "")
                    votes[group] = int(raw) if raw.lstrip("-").isdigit() else None
            dem = next((v for k, v in votes.items() if "dem" in k.lower() and v is not None), None)
            rep = next((v for k, v in votes.items() if "rep" in k.lower() and v is not None), None)
            if dem is None or rep is None or (dem + rep) == 0:
                continue  # not a real two-party contest here -- left out, not fabricated
            winner_party = cells[-1].split()[0] if cells[-1] else None
            out[district] = StateDistrictResult(
                district=district,
                dem_share=round(dem / (dem + rep) * 100, 2),
                winner_party=winner_party,
            )
        if out:
            return out
    return None


def fetch_state_house_results(state_name: str, year: int) -> dict[int, StateDistrictResult] | None:
    """Real two-party dem_share per district for one state+year, parsed from
    that state's own "{year} United States House of Representatives
    elections in {state_name}" Wikipedia page. Only returns data when a
    trustworthy per-district summary table was actually found (see
    _parse_district_results_table) -- None otherwise, so callers never
    silently backfill a guess."""
    title = f"{year}_United_States_House_of_Representatives_elections_in_{state_name.replace(' ', '_')}"
    html = fetch_wikipedia_html(title)
    if html is None:
        return None
    soup = BeautifulSoup(html, "html.parser")
    return _parse_district_results_table(soup)


def _clean_footnotes(text: str) -> str:
    # Also strips stray soft hyphens (U+00AD) -- Wikipedia inserts these
    # inside some words (e.g. "Vac\xadant") as invisible line-break hints,
    # which would otherwise silently break exact-string checks like
    # `.startswith("vacant")` below -- and non-breaking spaces (U+00A0),
    # which Wikipedia sometimes inserts inside a name (e.g. "Van\xa0Orden")
    # as a line-break hint between words. Left unnormalized, the same
    # person's name can come out byte-different depending on whether it was
    # read from the Member column or the Candidates cell, which breaks the
    # exact-string dedup check in _build_candidates and produces a phantom
    # duplicate candidate (see wi03, caught by hand -- 2026-07-27).
    return _FOOTNOTE_RE.sub("", text).replace("\xad", "").replace("\xa0", " ").strip()


def _wiki_page_title_for(name: str, cell: Tag) -> str | None:
    """Finds `name`'s own Wikipedia article title from a real <a href="/wiki/...">
    in `cell` whose link text matches -- never a guess built from the name
    itself (that could easily land on a wrong/disambiguation page)."""
    for a in cell.find_all("a"):
        href = a.get("href") or ""
        if href.startswith("/wiki/") and a.get_text(strip=True) == name:
            return href.removeprefix("/wiki/")
    return None


def _parse_candidates_cell(cell: Tag) -> list[ScrapedCandidate]:
    """Splits a "▌ Name (Party) ...  ▌ Name (Party) ..." cell into
    candidates. Real vote-share percentages/footnotes trailing a name are
    simply outside the regex match and dropped -- only name+party are
    trusted from this cell."""
    text = cell.get_text(" ", strip=True)
    candidates = []
    for token in _clean_footnotes(text).split(_BULLET):
        token = token.strip()
        if not token:
            continue
        match = _CANDIDATE_RE.match(token)
        if not match:
            continue
        name = match.group(1).strip()
        candidates.append(
            ScrapedCandidate(name=name, party=match.group(2).strip(), wiki_page_title=_wiki_page_title_for(name, cell))
        )
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

        all_candidates = _parse_candidates_cell(cells[-1])
        incumbent_wiki_page_title = (
            None if is_open_seat or member_idx is None else _wiki_page_title_for(member_name, cells[member_idx])
        )

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
                incumbent_wiki_page_title=incumbent_wiki_page_title,
            )
        )

    return districts


@lru_cache(maxsize=1)
def _fetch_house_elections_page_html() -> str | None:
    """Caches the one big "2026 House elections" page for the lifetime of
    the calling process -- fetch_all_districts and fetch_redistricting_changes
    both parse this same page, and every one-off script in backend/scripts
    that backfills House data tends to call both in a single run, so without
    this they'd download it twice for no reason. Scoped to this module (not
    a blanket cache on fetch_wikipedia_html itself) since that function is
    also used by the live scheduler's poll fetchers
    (app.ingestion.generic_ballot_scraper, approval_scraper), which need a
    genuinely fresh fetch on every scheduled run within the long-lived
    backend process -- caching there would silently freeze those at their
    first-ever fetch forever."""
    return fetch_wikipedia_html(HOUSE_ELECTIONS_PAGE_TITLE)


def fetch_all_districts() -> list[ScrapedDistrict]:
    """Fetches and parses every state's district table. Returns [] (rather
    than raising) if the page can't be fetched at all, same fail-soft
    convention as app.ingestion.wikipedia_scraper.fetch_general_election_polls
    -- a scheduled/manual re-run should never crash on a transient network
    error."""
    html = _fetch_house_elections_page_html()
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
    html = _fetch_house_elections_page_html()
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
