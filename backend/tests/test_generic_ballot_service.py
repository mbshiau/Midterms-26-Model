from datetime import date

import pytest

from app.database import Base
from app.ingestion.generic_ballot_scraper import ScrapedGenericBallot
from app.services.generic_ballot import (
    get_current_generic_ballot,
    seed_default_generic_ballot,
    update_generic_ballot,
)


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


def test_seed_default_generic_ballot_uses_static_researched_value(db_session, tables):
    row = seed_default_generic_ballot(db_session)
    assert row.dem_pct == 47.8
    assert row.rep_pct == 42.0


def test_seed_default_generic_ballot_is_idempotent(db_session, tables):
    first = seed_default_generic_ballot(db_session)
    second = seed_default_generic_ballot(db_session)
    assert first.id == second.id


def test_get_current_generic_ballot_seeds_if_empty(db_session, tables):
    row = get_current_generic_ballot(db_session)
    assert row.dem_pct == 47.8


def test_update_generic_ballot_overwrites_in_place_without_new_rows(db_session, tables):
    seed_default_generic_ballot(db_session)

    scraped = ScrapedGenericBallot(
        dem_pct=49.0,
        rep_pct=41.0,
        as_of=date(2026, 8, 1),
        source_url="https://en.wikipedia.org/wiki/2026_United_States_House_of_Representatives_elections",
    )
    updated = update_generic_ballot(db_session, scraped)

    assert updated.dem_pct == 49.0
    assert updated.rep_pct == 41.0
    assert updated.as_of == date(2026, 8, 1)

    all_rows = db_session.query(type(updated)).all()
    assert len(all_rows) == 1  # upserted in place, not accumulated
