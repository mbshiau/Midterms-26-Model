"""DB read/write helpers for a race's recent news headlines (see
app.ingestion.news_scraper). Display-only, like Kalshi -- never fed into
app.services.forecasting.generate_forecast.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ingestion.news_scraper import ScrapedNewsArticle, filter_relevant_articles
from app.models import NewsArticle

ARTICLES_PER_RACE = 10
# "Latest News" means recent -- a race with sparse coverage could otherwise
# keep showing a months-old headline forever just because fewer than
# ARTICLES_PER_RACE newer ones have come in to push it out.
MAX_ARTICLE_AGE_DAYS = 14


def _age_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)


def get_recent_news(db: Session, race_id: int) -> list[NewsArticle]:
    return (
        db.query(NewsArticle)
        .filter(NewsArticle.race_id == race_id, NewsArticle.published_at >= _age_cutoff())
        .order_by(NewsArticle.published_at.desc())
        .limit(ARTICLES_PER_RACE)
        .all()
    )


def update_news(db: Session, race_id: int, scraped: list[ScrapedNewsArticle]) -> int:
    """Upserts `scraped` by (race_id, url), then prunes anything older than
    MAX_ARTICLE_AGE_DAYS and anything beyond the ARTICLES_PER_RACE most
    recent rows for this race. Returns the count of genuinely new rows
    inserted this call (unused by callers today, but a natural signal for
    future "what's new" UI -- kept rather than discarded)."""
    existing_by_url = {
        row.url: row for row in db.query(NewsArticle).filter(NewsArticle.race_id == race_id).all()
    }

    new_count = 0
    for article in scraped:
        existing = existing_by_url.get(article.url)
        if existing is not None:
            existing.headline = article.headline
            existing.source = article.source
            existing.published_at = article.published_at
            continue
        db.add(
            NewsArticle(
                race_id=race_id,
                headline=article.headline,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
            )
        )
        new_count += 1

    db.commit()

    keep_ids = {
        row.id
        for row in db.query(NewsArticle)
        .filter(NewsArticle.race_id == race_id, NewsArticle.published_at >= _age_cutoff())
        .order_by(NewsArticle.published_at.desc())
        .limit(ARTICLES_PER_RACE)
        .all()
    }
    stale = (
        db.query(NewsArticle)
        .filter(NewsArticle.race_id == race_id, NewsArticle.id.notin_(keep_ids))
        .all()
    )
    for row in stale:
        db.delete(row)
    db.commit()

    return new_count


def purge_irrelevant_articles(db: Session, race_id: int, state_name: str, other_state_names: list[str]) -> int:
    """Re-checks every currently-stored article for this race against
    filter_relevant_articles and deletes any that now fail it.

    update_news's own pruning only drops rows by age or by rank beyond
    ARTICLES_PER_RACE -- it has no way to remove a row that's still recent
    and the race has few enough articles that it was never pushed out by
    count, even though it should never have been stored in the first place
    (e.g. articles ingested before filter_relevant_articles existed, or from
    before a change to it). Returns the count of rows removed."""
    existing = db.query(NewsArticle).filter(NewsArticle.race_id == race_id).all()
    relevant_ids = {a.id for a in filter_relevant_articles(existing, state_name, other_state_names)}
    irrelevant = [a for a in existing if a.id not in relevant_ids]
    for row in irrelevant:
        db.delete(row)
    if irrelevant:
        db.commit()
    return len(irrelevant)
