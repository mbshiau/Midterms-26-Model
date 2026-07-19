"""Live news-headline fetcher: pulls recent coverage of a race from Google
News' public RSS search feed.

Google News RSS is free and keyless, like Wikipedia (see wikipedia_scraper.py)
and unlike Kalshi -- no account or paid API required, just a plain GET. This
is display-only context for the Race Intelligence section (see
app.services.news / app.services.ai_summary); it never feeds
app.services.forecasting.generate_forecast.

Returns [] on any failure (bad response, unparseable XML, network error) --
same convention as every other scraper returning None on failure, just
list-shaped since callers here want "no headlines yet" rather than
"couldn't determine a single value".
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "PA-Gov-Forecast-Bot/1.0 (educational project; contact: admin@example.com)"
RSS_BASE_URL = "https://news.google.com/rss/search"
REQUEST_TIMEOUT_SECONDS = 15
MAX_ARTICLES = 10


@dataclass
class ScrapedNewsArticle:
    headline: str
    source: str
    url: str
    published_at: datetime


def _parse_item(item: ElementTree.Element) -> ScrapedNewsArticle | None:
    title = item.findtext("title")
    link = item.findtext("link")
    pub_date = item.findtext("pubDate")
    if not title or not link or not pub_date:
        return None

    try:
        published_at = parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return None
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    source_el = item.find("source")
    # Google News prefixes the title with " - <source>"; the <source> element
    # carries the same name structured, so prefer it and fall back to
    # whatever's in the title if it's ever missing.
    source = source_el.text.strip() if source_el is not None and source_el.text else "Unknown source"

    return ScrapedNewsArticle(headline=title.strip(), source=source, url=link.strip(), published_at=published_at)


def fetch_race_news(query: str) -> list[ScrapedNewsArticle]:
    """Fetches up to MAX_ARTICLES recent headlines matching `query`, newest
    first. Empty list (not None) on any failure -- a scrape hiccup means
    "no headlines this refresh", not "forecast refresh should abort"."""
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    url = f"{RSS_BASE_URL}?{urlencode(params)}"

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
    except (httpx.HTTPError, ElementTree.ParseError) as e:
        logger.warning("news fetch failed for query %r: %s", query, e)
        return []

    articles: list[ScrapedNewsArticle] = []
    for item in root.iter("item"):
        parsed = _parse_item(item)
        if parsed is not None:
            articles.append(parsed)
        if len(articles) >= MAX_ARTICLES:
            break

    articles.sort(key=lambda a: a.published_at, reverse=True)
    return articles


def build_news_query(state_name: str, office: str) -> str:
    """The search query Google News RSS runs against -- state + office is
    specific enough to surface race coverage without being so narrow (e.g.
    candidate names) that it misses stories that mention the race generically."""
    return f"{state_name} {office} election"
