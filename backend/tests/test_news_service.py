from datetime import date, datetime, timedelta, timezone

import pytest

from app.database import Base
from app.ingestion.news_scraper import ScrapedNewsArticle
from app.models import NewsArticle, Race
from app.services.news import (
    ARTICLES_PER_RACE,
    MAX_ARTICLE_AGE_DAYS,
    get_recent_news,
    purge_irrelevant_articles,
    update_news,
)


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture()
def race(db_session, tables):
    r = Race(
        state_code="zz",
        state_name="Test State",
        election_date=date(2026, 11, 3),
        wikipedia_page_title="Test",
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


def _article(n: int, published_at: datetime) -> ScrapedNewsArticle:
    return ScrapedNewsArticle(
        headline=f"Headline {n}",
        source="Example News",
        url=f"https://example.com/{n}",
        published_at=published_at,
    )


def test_update_news_inserts_new_articles_and_returns_count(db_session, race):
    now = datetime.now(timezone.utc)
    scraped = [_article(1, now), _article(2, now - timedelta(hours=1))]

    new_count = update_news(db_session, race.id, scraped)

    assert new_count == 2
    assert len(get_recent_news(db_session, race.id)) == 2


def test_update_news_upserts_existing_articles_by_url_without_duplicating(db_session, race):
    now = datetime.now(timezone.utc)
    first = _article(1, now)
    update_news(db_session, race.id, [first])

    updated = ScrapedNewsArticle(
        headline="Updated headline", source=first.source, url=first.url, published_at=now
    )
    new_count = update_news(db_session, race.id, [updated])

    assert new_count == 0  # same URL -- upserted, not a new row
    articles = get_recent_news(db_session, race.id)
    assert len(articles) == 1
    assert articles[0].headline == "Updated headline"


def test_update_news_prunes_to_most_recent_n_per_race(db_session, race):
    now = datetime.now(timezone.utc)
    scraped = [_article(i, now - timedelta(hours=i)) for i in range(ARTICLES_PER_RACE + 5)]

    update_news(db_session, race.id, scraped)

    articles = get_recent_news(db_session, race.id)
    assert len(articles) == ARTICLES_PER_RACE
    # kept the newest ones (smallest offset = most recent)
    assert all(a.headline in {f"Headline {i}" for i in range(ARTICLES_PER_RACE)} for a in articles)


def test_get_recent_news_returns_empty_list_for_race_with_no_articles(db_session, race):
    assert get_recent_news(db_session, race.id) == []


def test_get_recent_news_omits_articles_older_than_the_age_cutoff(db_session, race):
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            NewsArticle(
                race_id=race.id,
                headline="Recent",
                source="Example",
                url="https://example.com/recent",
                published_at=now - timedelta(days=MAX_ARTICLE_AGE_DAYS - 1),
            ),
            NewsArticle(
                race_id=race.id,
                headline="Stale",
                source="Example",
                url="https://example.com/stale",
                published_at=now - timedelta(days=MAX_ARTICLE_AGE_DAYS + 1),
            ),
        ]
    )
    db_session.commit()

    headlines = {a.headline for a in get_recent_news(db_session, race.id)}
    assert headlines == {"Recent"}


def test_update_news_prunes_articles_older_than_the_age_cutoff(db_session, race):
    now = datetime.now(timezone.utc)
    scraped = [
        _article(1, now),
        _article(2, now - timedelta(days=MAX_ARTICLE_AGE_DAYS + 1)),
    ]

    update_news(db_session, race.id, scraped)

    remaining = db_session.query(NewsArticle).filter(NewsArticle.race_id == race.id).all()
    assert [a.headline for a in remaining] == ["Headline 1"]


def test_purge_irrelevant_articles_removes_rows_naming_a_different_state(db_session, race):
    # Regression test for a real observed bug: rows stored before
    # filter_relevant_articles existed (or before a query tightening) stay
    # forever otherwise -- update_news's own pruning only drops rows by age
    # or by rank beyond ARTICLES_PER_RACE, neither of which catches a
    # recent, small-count race's already-stored bad headline.
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            NewsArticle(
                race_id=race.id,
                headline="Nebraska Governor Election 2026: Latest Polls",
                source="Example",
                url="https://example.com/other-state",
                published_at=now,
            ),
            NewsArticle(
                race_id=race.id,
                headline="Test State governor race tightens ahead of debate",
                source="Example",
                url="https://example.com/relevant",
                published_at=now,
            ),
        ]
    )
    db_session.commit()

    purged = purge_irrelevant_articles(db_session, race.id, "Test State", ["Nebraska"])

    assert purged == 1
    remaining = db_session.query(NewsArticle).filter(NewsArticle.race_id == race.id).all()
    assert [a.headline for a in remaining] == ["Test State governor race tightens ahead of debate"]


def test_purge_irrelevant_articles_returns_zero_when_nothing_to_remove(db_session, race):
    db_session.add(
        NewsArticle(
            race_id=race.id,
            headline="Headline with no state name",
            source="Example",
            url="https://example.com/ok",
            published_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    assert purge_irrelevant_articles(db_session, race.id, "Test State", ["Nebraska"]) == 0
