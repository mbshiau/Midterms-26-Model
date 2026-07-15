"""Live generic-congressional-ballot fetcher: pulls the cross-aggregator
"Average" row from Wikipedia's House-elections opinion-polling table. Same
rationale as approval_scraper.py / wikipedia_scraper.py — this is the
ToS-compliant, bot-friendly source; individual aggregators aren't.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from app.ingestion.wikipedia_scraper import fetch_wikipedia_html, parse_full_date

logger = logging.getLogger(__name__)

DEFAULT_PAGE_TITLE = "2026_United_States_House_of_Representatives_elections"
DEFAULT_SECTION_HEADERS = ("aggregation", "republicans", "democrats")


@dataclass
class ScrapedGenericBallot:
    dem_pct: float
    rep_pct: float
    as_of: date
    source_url: str


def fetch_current_generic_ballot(page_title: str = DEFAULT_PAGE_TITLE) -> ScrapedGenericBallot | None:
    html = fetch_wikipedia_html(page_title)
    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")
    table = None
    for candidate_table in soup.find_all("table", class_="wikitable"):
        header_row = candidate_table.find("tr")
        if header_row is None:
            continue
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all("th")]
        header_blob = " ".join(headers)
        if all(h in header_blob for h in DEFAULT_SECTION_HEADERS):
            table = candidate_table
            break

    if table is None:
        logger.warning("no generic-ballot-aggregate table found on %r", page_title)
        return None

    average_row = None
    for row in table.find_all("tr")[1:]:
        first_cell = row.find(["td", "th"])
        if first_cell and first_cell.get_text(strip=True).lower() == "average":
            average_row = row
            break

    if average_row is None:
        logger.warning("no 'Average' row found in generic-ballot table on %r", page_title)
        return None

    # cells: [0]="Average" label, [1]=Updated date, [2]=Republicans, [3]=Democrats, ...
    cells = average_row.find_all("td")
    if len(cells) < 4:
        return None

    updated = parse_full_date(cells[1].get_text(strip=True))
    rep_match = re.search(r"([\d.]+)", cells[2].get_text(strip=True))
    dem_match = re.search(r"([\d.]+)", cells[3].get_text(strip=True))

    if updated is None or not rep_match or not dem_match:
        return None

    return ScrapedGenericBallot(
        dem_pct=float(dem_match.group(1)),
        rep_pct=float(rep_match.group(1)),
        as_of=updated,
        source_url=f"https://en.wikipedia.org/wiki/{page_title}",
    )
