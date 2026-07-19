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
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Protocol, TypeVar
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
    """The search query Google News RSS runs against. Quoting "<state>
    <office>" forces Google to require that phrase rather than doing a loose
    keyword match -- unquoted, a query like "Texas Governor election" was
    observed pulling in unrelated same-topic roundups, e.g. NYT's templated
    "<Other State> Governor Election 2026: Latest Polls" series and stories
    about a different state's candidate, neither of which mention Texas at
    all. `election` stays unquoted outside the phrase as a loose relevance
    signal. See also filter_relevant_articles for a second line of defense
    against whatever still slips through."""
    return f'"{state_name} {office}" election'


class _HasHeadline(Protocol):
    headline: str


_T = TypeVar("_T", bound=_HasHeadline)


def filter_relevant_articles(articles: list[_T], state_name: str, other_state_names: list[str]) -> list[_T]:
    """Drops articles whose headline names a *different* state and doesn't
    name this race's own state -- the concrete failure mode seen from the
    unquoted query above (a same-topic roundup about another state's
    governor race). Kept deliberately permissive otherwise: plenty of
    genuinely relevant headlines (e.g. "Becerra leads in new statewide
    poll") never mention the state by name at all, so this only rejects
    headlines that give a *positive* signal of being about somewhere else.

    Generic over anything with a `.headline` string -- used both on freshly
    scraped ScrapedNewsArticle batches and on already-stored NewsArticle ORM
    rows (see app.services.news.purge_irrelevant_articles), since a row
    stored before this filter existed needs the exact same check applied
    retroactively."""
    own_pattern = re.compile(rf"\b{re.escape(state_name)}\b", re.IGNORECASE)
    other_patterns = [re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE) for name in other_state_names]

    kept = []
    for article in articles:
        if own_pattern.search(article.headline):
            kept.append(article)
            continue
        if any(pattern.search(article.headline) for pattern in other_patterns):
            continue
        kept.append(article)
    return kept
