"""Live poll fetcher: pulls the general-election polling table from Wikipedia
via the MediaWiki API and parses it into the same raw-poll shape as
app.seed.seed_data.RAW_POLLS.

Real-time poll aggregators (RealClearPolling, 270toWin) return 403 to
automated requests — their ToS doesn't permit scraping. Wikipedia's API is
explicitly built for programmatic use (with a descriptive User-Agent and
reasonable request volume), which is why this targets it instead. The
tradeoff: it only picks up a poll once a Wikipedia editor has added it, so
it lags a live tracker by however long that takes.

release_date isn't given by this table (only the field dates are), so it's
approximated as field_end_date + RELEASE_DATE_LAG_DAYS, same convention
used for the manually-curated seed polls.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

USER_AGENT = "PA-Gov-Forecast-Bot/1.0 (educational project; contact: admin@example.com)"
API_URL = "https://en.wikipedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 15
RELEASE_DATE_LAG_DAYS = 3

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ],
        start=1,
    )
}


def parse_full_date(text: str) -> date | None:
    """Parses a single "Month D, Year" date, e.g. "July 10, 2026" -- the
    format Wikipedia's aggregate-tracker tables (presidential approval,
    generic congressional ballot) use for their "Updated" column."""
    match = re.match(r"^(\w+)\s+(\d{1,2}),?\s*(\d{4})$", text.strip())
    if not match:
        return None
    month_name, day, year = match.groups()
    month = MONTHS.get(month_name.lower())
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


@dataclass
class ScrapedPoll:
    pollster: str
    field_start_date: date
    field_end_date: date
    release_date: date
    sample_size: int
    population: str
    margin_of_error: float | None
    undecided_pct: float
    source_url: str
    results: dict[str, float]


def fetch_wikipedia_html(page_title: str) -> str | None:
    try:
        resp = httpx.get(
            API_URL,
            params={
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text",
                "formatversion": 2,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()["parse"]["text"]
    except (httpx.HTTPError, KeyError) as e:
        logger.warning("Wikipedia fetch failed for %r: %s", page_title, e)
        return None


def fetch_page_thumbnail(page_title: str, size: int = 500) -> str | None:
    """Real infobox/lead image for a Wikipedia article (e.g. a politician's
    official photo), via MediaWiki's pageimages API -- the same thumbnail
    Wikipedia itself shows, at `size`px wide. Used by
    scripts/backfill_candidate_photos.py to fill in a candidate's photo_url
    from their own article (see app.ingestion.house_scraper's
    wiki_page_title capture) rather than guessing a Commons filename.
    Returns None if the page has no image, doesn't exist, or the request
    fails -- never fabricated."""
    try:
        resp = httpx.get(
            API_URL,
            params={
                "action": "query",
                "titles": page_title,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": size,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        pages = resp.json()["query"]["pages"]
        page = next(iter(pages.values()))
        return page.get("thumbnail", {}).get("source")
    except (httpx.HTTPError, KeyError, StopIteration) as e:
        logger.warning("Wikipedia thumbnail fetch failed for %r: %s", page_title, e)
        return None


def _header_texts(table: Tag) -> list[str]:
    header_row = table.find("tr")
    if header_row is None:
        return []
    # get_text(" ", ...) -- NOT the bare/no-separator get_text() -- because a
    # <br/> between two words in a header (e.g. Wikipedia wrapping a two-word
    # surname mid-name: "Monica De<br/>La Cruz (R)") otherwise collapses to
    # "monica dela cruz (r)" with no separator at all, merging "de" and "la"
    # into one word. The surname-matching in _find_polling_table then does a
    # plain substring check for "de la cruz", which never matches "dela
    # cruz" -- silently and permanently missing that candidate's real
    # polling table on every scheduled refresh, not just once.
    return [th.get_text(" ", strip=True).lower() for th in header_row.find_all(["th"])]


def _extra_candidate_column_count(headers: list[str], surnames_lower: list[str]) -> int:
    """Counts header columns that look like a *different* candidate's name
    (a "Firstname Lastname (D/R/I)" column not belonging to any of our
    target surnames) -- i.e. how many nominees this table tests beyond our
    race's actual two (or more). A pre-primary "trial heat" table testing
    several hypothetical matchups happens to mention our eventual nominees
    too (they were primary candidates once), so requiring the surnames to
    merely be *present* isn't enough to find the real general-election
    table -- it has to be the one where they're the *only* candidates."""
    return sum(
        1
        for h in headers
        if re.search(r"\([dri]\)\s*$", h) and not any(s in h for s in surnames_lower)
    )


def _find_polling_table(soup: BeautifulSoup, candidate_surnames: list[str]) -> Tag | None:
    surnames_lower = [s.lower() for s in candidate_surnames]
    matches: list[tuple[int, Tag]] = []
    for table in soup.find_all("table", class_="wikitable"):
        headers = _header_texts(table)
        header_blob = " ".join(headers)
        if "sample" not in header_blob or "poll source" not in header_blob:
            continue
        if all(surname in header_blob for surname in surnames_lower):
            matches.append((_extra_candidate_column_count(headers, surnames_lower), table))

    if not matches:
        return None

    # Prefer an exact head-to-head match (no extra candidates beyond our
    # race's own) -- a table that also tests other hypothetical nominees is
    # a primary-era trial heat, not the actual general-election polling
    # table. Among equally-exact matches, the later one in document order is
    # the real one: Wikipedia lists primary-era trial heats before the
    # (post-primary) general-election polling section.
    min_extra = min(extra for extra, _ in matches)
    return [table for extra, table in matches if extra == min_extra][-1]


def _clean_pollster_name(cell: Tag) -> str:
    for sup in cell.find_all("sup"):
        sup.decompose()
    text = cell.get_text(strip=True)
    # strip a trailing partisan-sponsor annotation, e.g. "Susquehanna ... (R)"
    return re.sub(r"\s*\([DRI]\)\s*$", "", text).strip()


def _parse_sample(text: str) -> tuple[int, str] | None:
    match = re.search(r"([\d,]+)\s*\(([A-Za-z]{1,2})\)", text)
    if not match:
        return None
    return int(match.group(1).replace(",", "")), match.group(2).upper()


def _parse_moe(text: str) -> float | None:
    match = re.search(r"([\d.]+)\s*%?", text.replace("±", ""))
    return float(match.group(1)) if match else None


def _parse_pct(text: str) -> float:
    text = text.strip()
    if text in ("–", "—", "-", ""):
        return 0.0
    match = re.search(r"([\d.]+)", text)
    return float(match.group(1)) if match else 0.0


def _parse_date_range(text: str, fallback_year: int) -> tuple[date, date] | None:
    text = text.replace("–", "-").replace("—", "-").strip()
    text = re.sub(r"^through\s+", "", text, flags=re.IGNORECASE)

    # "Month D, Year" (single day, no range)
    single = re.match(r"^(\w+)\s+(\d{1,2}),?\s*(\d{4})?$", text)
    # "Month D - D, Year" (same month)
    same_month = re.match(r"^(\w+)\s+(\d{1,2})\s*-\s*(\d{1,2}),?\s*(\d{4})$", text)
    # "Month D - Month D, Year" (crosses months)
    cross_month = re.match(
        r"^(\w+)\s+(\d{1,2})\s*-\s*(\w+)\s+(\d{1,2}),?\s*(\d{4})$", text
    )

    try:
        if cross_month:
            m1, d1, m2, d2, year = cross_month.groups()
            year = int(year)
            start = date(year, MONTHS[m1.lower()], int(d1))
            end = date(year, MONTHS[m2.lower()], int(d2))
            return start, end
        if same_month:
            m1, d1, d2, year = same_month.groups()
            year = int(year)
            month = MONTHS[m1.lower()]
            return date(year, month, int(d1)), date(year, month, int(d2))
        if single:
            m1, d1, year = single.groups()
            year = int(year) if year else fallback_year
            day = date(year, MONTHS[m1.lower()], int(d1))
            return day, day
    except (KeyError, ValueError):
        return None
    return None


def _parse_rows(table: Tag, candidate_columns: dict[str, int], source_url: str) -> list[ScrapedPoll]:
    header_texts = _header_texts(table)
    try:
        sample_idx = next(i for i, h in enumerate(header_texts) if "sample" in h)
        date_idx = next(i for i, h in enumerate(header_texts) if "date" in h)
        moe_idx = next((i for i, h in enumerate(header_texts) if "margin" in h), None)
        other_idx = next((i for i, h in enumerate(header_texts) if h == "other"), None)
        undecided_idx = next((i for i, h in enumerate(header_texts) if "undecided" in h), None)
    except StopIteration:
        return []

    polls: list[ScrapedPoll] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) <= max(sample_idx, date_idx, *candidate_columns.values()):
            continue
        if cells[0].get("colspan"):  # summary/average row
            continue

        pollster = _clean_pollster_name(cells[0])
        date_range = _parse_date_range(cells[date_idx].get_text(strip=True), fallback_year=date.today().year)
        sample = _parse_sample(cells[sample_idx].get_text(strip=True))
        if not pollster or date_range is None or sample is None:
            continue

        # moe/other/undecided are optional columns whose *header* index was
        # found, but an individual row can still be shorter than the header
        # implies (a ragged Wikipedia table row) -- guard each access
        # separately rather than assuming every row has every column, or a
        # single malformed row crashes the whole scheduled refresh (and,
        # since that loop covers every state, silently blocks every race
        # after this one too).
        def cell_at(idx: int | None) -> str | None:
            return cells[idx].get_text(strip=True) if idx is not None and idx < len(cells) else None

        results = {name: _parse_pct(cells[idx].get_text(strip=True)) for name, idx in candidate_columns.items()}
        other_text = cell_at(other_idx)
        undecided_text = cell_at(undecided_idx)
        other = _parse_pct(other_text) if other_text is not None else 0.0
        undecided = _parse_pct(undecided_text) if undecided_text is not None else 0.0
        moe_text = cell_at(moe_idx)

        field_start, field_end = date_range
        polls.append(
            ScrapedPoll(
                pollster=pollster,
                field_start_date=field_start,
                field_end_date=field_end,
                release_date=field_end + timedelta(days=RELEASE_DATE_LAG_DAYS),
                sample_size=sample[0],
                population=sample[1],
                margin_of_error=_parse_moe(moe_text) if moe_text is not None else None,
                undecided_pct=round(other + undecided, 2),
                source_url=source_url,
                results=results,
            )
        )

    return polls


def fetch_general_election_polls(
    page_title: str, candidate_names: dict[str, str]
) -> list[ScrapedPoll]:
    """candidate_names maps a Wikipedia header surname (e.g. "Shapiro") to
    the full candidate name as stored in our DB (e.g. "Josh Shapiro")."""
    html = fetch_wikipedia_html(page_title)
    if html is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    return polls_from_soup(soup, page_title, candidate_names)


def polls_from_soup(
    soup: BeautifulSoup, page_title: str, candidate_names: dict[str, str]
) -> list[ScrapedPoll]:
    """Same extraction as fetch_general_election_polls, against an
    already-fetched-and-parsed page. Most House districts share one combined
    Wikipedia page (413 of 435 races point at the same
    "2026_United_States_House_of_Representatives_elections" article as of
    2026) -- a caller refreshing every race in a loop should fetch + parse
    that page once and pass the same soup in for every race that shares it,
    rather than re-fetching and re-parsing an identical multi-hundred-KB page
    hundreds of times. That redundant per-race fetch was the actual cause of
    the scheduled refresh job taking 15-100+ minutes and timing out the
    Render free-tier / GitHub Actions trigger (see scheduler.py)."""
    table = _find_polling_table(soup, list(candidate_names.keys()))
    if table is None:
        logger.warning("no matching polling table found on %r", page_title)
        return []

    header_texts = _header_texts(table)
    candidate_columns = {}
    for surname, full_name in candidate_names.items():
        idx = next((i for i, h in enumerate(header_texts) if surname.lower() in h), None)
        if idx is not None:
            candidate_columns[full_name] = idx

    if len(candidate_columns) != len(candidate_names):
        logger.warning("could not locate all candidate columns on %r", page_title)
        return []

    source_url = f"https://en.wikipedia.org/wiki/{page_title}"
    return _parse_rows(table, candidate_columns, source_url)
