from datetime import date

import pytest

from app.database import Base
from app.ingestion.approval_scraper import ScrapedApproval
from app.services.approval import get_current_approval, seed_default_approval, update_approval


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


def test_seed_default_approval_uses_static_researched_value(db_session, tables):
    row = seed_default_approval(db_session)
    assert row.name == "Donald Trump"
    assert row.party == "Republican"
    assert row.approval_pct == 37.0


def test_seed_default_approval_is_idempotent(db_session, tables):
    first = seed_default_approval(db_session)
    second = seed_default_approval(db_session)
    assert first.id == second.id


def test_get_current_approval_seeds_if_empty(db_session, tables):
    row = get_current_approval(db_session)
    assert row.approval_pct == 37.0


def test_update_approval_overwrites_in_place_without_new_rows(db_session, tables):
    seed_default_approval(db_session)

    scraped = ScrapedApproval(
        approval_pct=41.2,
        disapproval_pct=55.0,
        as_of=date(2026, 8, 1),
        source_url="https://en.wikipedia.org/wiki/Opinion_polling_on_the_second_Trump_presidency",
    )
    updated = update_approval(db_session, scraped, party="Republican", name="Donald Trump")

    assert updated.approval_pct == 41.2
    assert updated.as_of == date(2026, 8, 1)

    all_rows = db_session.query(type(updated)).all()
    assert len(all_rows) == 1  # upserted in place, not accumulated
