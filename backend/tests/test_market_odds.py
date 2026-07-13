from datetime import date, datetime, timezone

import pytest

from app.database import Base
from app.ingestion.kalshi_scraper import ScrapedMarketOdds
from app.models import Candidate, Race
from app.services.market_odds import get_market_odds, update_market_odds


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture()
def candidate(db_session, tables):
    race = Race(
        state_code="zz",
        state_name="Test State",
        election_date=date(2026, 11, 3),
        wikipedia_page_title="Test",
    )
    db_session.add(race)
    db_session.flush()
    cand = Candidate(race_id=race.id, name="Test Candidate", party="Democratic", kalshi_ticker="KXTEST-26-CAND")
    db_session.add(cand)
    db_session.commit()
    db_session.refresh(cand)
    return cand


def test_get_market_odds_returns_empty_when_no_rows(db_session, candidate):
    assert get_market_odds(db_session, [candidate.id]) == {}


def test_get_market_odds_returns_empty_for_no_candidate_ids(db_session, tables):
    assert get_market_odds(db_session, []) == {}


def test_update_market_odds_creates_then_upserts_in_place(db_session, candidate):
    first = ScrapedMarketOdds(
        ticker="KXTEST-26-CAND",
        yes_price_pct=65.0,
        as_of=datetime(2026, 7, 1, tzinfo=timezone.utc),
        source_url="https://kalshi.com/markets/kxtest-26-cand",
    )
    row = update_market_odds(db_session, candidate.id, first)
    assert row.yes_price_pct == 65.0

    second = ScrapedMarketOdds(
        ticker="KXTEST-26-CAND",
        yes_price_pct=71.0,
        as_of=datetime(2026, 7, 2, tzinfo=timezone.utc),
        source_url="https://kalshi.com/markets/kxtest-26-cand",
    )
    updated = update_market_odds(db_session, candidate.id, second)
    assert updated.yes_price_pct == 71.0
    assert updated.id == row.id  # upserted in place, not accumulated

    all_rows = db_session.query(type(updated)).all()
    assert len(all_rows) == 1

    lookup = get_market_odds(db_session, [candidate.id])
    assert lookup[candidate.id].yes_price_pct == 71.0
