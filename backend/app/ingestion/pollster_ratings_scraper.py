"""Live pollster-quality-ratings fetcher: pulls PollingSource.com's full
/pollsters table (historical average error, partisan lean, and winner-call
rate per pollster, across every tracked election cycle).

Unlike Wikipedia's approval/generic-ballot tables (one "Average" row),
this is a whole-table scrape -- every row is a different pollster. Chosen
over the alternatives because there is currently no other clean, free,
static-HTML source for this: FiveThirtyEight's pollster ratings tool was
shut down by ABC News in 2023, and Nate Silver's Silver Bulletin successor
distributes its ratings as downloadable spreadsheets behind a partial
paywall, not a scrapable HTML table. PollingSource's robots.txt explicitly
allows crawling (`Allow: /`) and the site publishes a documented, free,
attribution-based JSON API for its other datasets, which is good evidence
this is an intentionally public data source rather than an incidental
scrape target -- but it's a much smaller, less established site than
Wikipedia, so treat its numbers as a useful signal, not ground truth.
"""

import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "PA-Gov-Forecast-Bot/1.0 (educational project; contact: admin@example.com)"
# A bare User-Agent with no Accept/Accept-Language header is itself a common
# bot signature -- PollingSource's anti-bot layer 403s a request missing
# these even though robots.txt explicitly allows crawling `/`.
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
RATINGS_URL = "https://pollingsource.com/pollsters"
REQUEST_TIMEOUT_SECONDS = 15


@dataclass
class ScrapedPollsterRating:
    pollster: str
    avg_error_pts: float | None
    lean_party: str | None
    lean_pts: float | None
    winner_called_pct: float | None
    polls_count: int | None
    cycles_count: int | None
    source_url: str


def _parse_error_pts(text: str) -> float | None:
    match = re.search(r"([\d.]+)\s*pts", text)
    return float(match.group(1)) if match else None


def _parse_pct(text: str) -> float | None:
    match = re.search(r"([\d.]+)\s*%", text)
    return float(match.group(1)) if match else None


def _parse_int(text: str) -> int | None:
    text = text.strip()
    return int(text) if text.isdigit() else None


def _parse_lean(text: str) -> tuple[str | None, float | None]:
    text = text.strip().upper()
    if text == "EVEN":
        return None, 0.0
    match = re.match(r"^([DR])\+([\d.]+)$", text)
    if not match:
        return None, None
    party = "Democratic" if match.group(1) == "D" else "Republican"
    return party, float(match.group(2))


def fetch_pollster_ratings(url: str = RATINGS_URL) -> list[ScrapedPollsterRating]:
    """Returns every row in the table. Returns [] on any failure -- a
    network error or an unexpected page structure should never crash the
    scheduled job, just leave existing ratings unchanged until next run."""
    try:
        resp = httpx.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        html = resp.text
    except httpx.HTTPError as e:
        logger.warning("pollster ratings fetch failed for %r: %s", url, e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        logger.warning("no ratings table found on %r", url)
        return []

    header_row = table.find("tr")
    if header_row is None:
        return []
    headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
    try:
        pollster_idx = headers.index("pollster")
        polls_idx = headers.index("polls")
        cycles_idx = headers.index("cycles")
        error_idx = headers.index("avg. error")
        lean_idx = headers.index("lean")
        winner_idx = headers.index("winner called")
    except ValueError:
        logger.warning("ratings table on %r is missing an expected column", url)
        return []

    ratings: list[ScrapedPollsterRating] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= max(pollster_idx, polls_idx, cycles_idx, error_idx, lean_idx, winner_idx):
            continue

        pollster = cells[pollster_idx].get_text(strip=True)
        if not pollster:
            continue

        lean_party, lean_pts = _parse_lean(cells[lean_idx].get_text(strip=True))
        ratings.append(
            ScrapedPollsterRating(
                pollster=pollster,
                avg_error_pts=_parse_error_pts(cells[error_idx].get_text(strip=True)),
                lean_party=lean_party,
                lean_pts=lean_pts,
                winner_called_pct=_parse_pct(cells[winner_idx].get_text(strip=True)),
                polls_count=_parse_int(cells[polls_idx].get_text(strip=True)),
                cycles_count=_parse_int(cells[cycles_idx].get_text(strip=True)),
                source_url=url,
            )
        )

    return ratings
