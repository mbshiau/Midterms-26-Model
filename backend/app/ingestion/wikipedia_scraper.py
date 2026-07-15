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


def _header_texts(table: Tag) -> list[str]:
    header_row = table.find("tr")
    if header_row is None:
        return []
    return [th.get_text(strip=True).lower() for th in header_row.find_all(["th"])]


def _find_polling_table(soup: BeautifulSoup, candidate_surnames: list[str]) -> Tag | None:
    surnames_lower = [s.lower() for s in candidate_surnames]
    for table in soup.find_all("table", class_="wikitable"):
        headers = _header_texts(table)
        header_blob = " ".join(headers)
        if "sample" not in header_blob or "poll source" not in header_blob:
            continue
        if all(surname in header_blob for surname in surnames_lower):
            return table
    return None


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
