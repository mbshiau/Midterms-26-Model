import pytest

from app.config import settings
from app.database import Base
from app.ingestion.pollster_ratings_scraper import ScrapedPollsterRating
from app.models import PollsterRating
from app.services.pollster_ratings import (
    get_pollster_ratings_by_name,
    normalize_pollster_name,
    pollster_quality_weight,
    upsert_pollster_ratings,
)


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


def _scraped(pollster="YouGov", avg_error_pts=5.2) -> ScrapedPollsterRating:
    return ScrapedPollsterRating(
        pollster=pollster,
        avg_error_pts=avg_error_pts,
        lean_party="Democratic",
        lean_pts=3.4,
        winner_called_pct=82.0,
        polls_count=443,
        cycles_count=7,
        source_url="https://pollingsource.com/pollsters",
    )


def test_normalize_pollster_name_lowercases_and_strips():
    assert normalize_pollster_name("  YouGov  ") == "yougov"
    assert normalize_pollster_name("YouGov") == normalize_pollster_name(" yougov ")


def test_upsert_pollster_ratings_creates_new_rows(db_session, tables):
    count = upsert_pollster_ratings(db_session, [_scraped()])

    assert count == 1
    rows = db_session.query(PollsterRating).all()
    assert len(rows) == 1
    assert rows[0].normalized_name == "yougov"
    assert rows[0].avg_error_pts == 5.2


def test_upsert_pollster_ratings_updates_in_place_without_duplicating(db_session, tables):
    upsert_pollster_ratings(db_session, [_scraped(avg_error_pts=5.2)])
    upsert_pollster_ratings(db_session, [_scraped(avg_error_pts=4.8)])

    rows = db_session.query(PollsterRating).all()
    assert len(rows) == 1  # upserted, not accumulated
    assert rows[0].avg_error_pts == 4.8


def test_get_pollster_ratings_by_name_keys_on_normalized_name(db_session, tables):
    upsert_pollster_ratings(db_session, [_scraped(pollster="YouGov")])

    ratings = get_pollster_ratings_by_name(db_session)

    assert "yougov" in ratings
    assert ratings["yougov"].pollster_name == "YouGov"


def test_pollster_quality_weight_is_neutral_when_no_error_figure_exists():
    assert pollster_quality_weight(None) == 1.0


def test_pollster_quality_weight_is_neutral_at_the_baseline():
    assert pollster_quality_weight(settings.pollster_baseline_error_pts) == pytest.approx(1.0)


def test_pollster_quality_weight_upweights_a_more_accurate_pollster():
    better_than_baseline = settings.pollster_baseline_error_pts / 2
    assert pollster_quality_weight(better_than_baseline) > 1.0


def test_pollster_quality_weight_downweights_a_less_accurate_pollster():
    worse_than_baseline = settings.pollster_baseline_error_pts * 2
    assert pollster_quality_weight(worse_than_baseline) < 1.0


def test_pollster_quality_weight_is_clipped_to_the_configured_floor_and_ceiling():
    extremely_bad = settings.pollster_baseline_error_pts * 1000
    extremely_good = settings.pollster_baseline_error_pts / 1000

    assert pollster_quality_weight(extremely_bad) == settings.pollster_quality_weight_floor
    assert pollster_quality_weight(extremely_good) == settings.pollster_quality_weight_ceiling
