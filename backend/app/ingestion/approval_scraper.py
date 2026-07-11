"""Live presidential-approval fetcher: pulls the cross-aggregator "Average"
row from Wikipedia's opinion-polling tracker page. Same rationale as
wikipedia_scraper.py — this is the ToS-compliant, bot-friendly source;
individual aggregators (RCP, Silver Bulletin, etc.) aren't.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from app.ingestion.wikipedia_scraper import MONTHS, fetch_wikipedia_html

logger = logging.getLogger(__name__)

DEFAULT_PAGE_TITLE = "Opinion_polling_on_the_second_Trump_presidency"
DEFAULT_SECTION_HEADERS = ("aggregator", "approve", "disapprove")


@dataclass
class ScrapedApproval:
    approval_pct: float
    disapproval_pct: float
    as_of: date
    source_url: str


def _parse_date(text: str) -> date | None:
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


def fetch_current_approval(page_title: str = DEFAULT_PAGE_TITLE) -> ScrapedApproval | None:
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
        logger.warning("no approval-aggregate table found on %r", page_title)
        return None

    average_row = None
    for row in table.find_all("tr")[1:]:
        first_cell = row.find(["td", "th"])
        if first_cell and first_cell.get_text(strip=True).lower() == "average":
            average_row = row
            break

    if average_row is None:
        logger.warning("no 'Average' row found in approval table on %r", page_title)
        return None

    # cells: [0]="Average" label, [1]=Updated date, [2]=Approve, [3]=Disapprove, ...
    cells = average_row.find_all("td")
    if len(cells) < 4:
        return None

    updated = _parse_date(cells[1].get_text(strip=True))
    approve_match = re.search(r"([\d.]+)", cells[2].get_text(strip=True))
    disapprove_match = re.search(r"([\d.]+)", cells[3].get_text(strip=True))

    if updated is None or not approve_match or not disapprove_match:
        return None

    return ScrapedApproval(
        approval_pct=float(approve_match.group(1)),
        disapproval_pct=float(disapprove_match.group(1)),
        as_of=updated,
        source_url=f"https://en.wikipedia.org/wiki/{page_title}",
    )
