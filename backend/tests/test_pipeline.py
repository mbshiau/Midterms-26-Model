from datetime import date
from unittest.mock import patch

import pytest

from app.database import Base
from app.ingestion.pipeline import fetch_live_polls, get_or_create_candidates, ingest_polls
from app.ingestion.wikipedia_scraper import ScrapedPoll
from app.models import Candidate, Race


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


def make_race(db_session, state_code="pa") -> Race:
    race = Race(
        state_code=state_code,
        state_name="Pennsylvania",
        office="Governor",
        election_date=date(2026, 11, 3),
        wikipedia_page_title="2026_Pennsylvania_gubernatorial_election",
    )
    db_session.add(race)
    db_session.commit()
    return race


def test_same_poll_cited_via_different_url_is_not_duplicated(db_session, tables):
    race = make_race(db_session)
    race_seed = {
        "candidates": [
            {"name": "Josh Shapiro", "party": "Democratic", "incumbent": True},
            {"name": "Stacy Garrity", "party": "Republican", "incumbent": False},
        ],
        "raw_polls": [],
    }

    def seed_fetcher(candidates):
        return [
            {
                "pollster": "Quinnipiac University",
                "sponsor": None,
                "field_start_date": "2026-02-19",
                "field_end_date": "2026-02-23",
                "release_date": "2026-02-25",
                "sample_size": 836,
                "population": "RV",
                "margin_of_error": 4.7,
                "undecided_pct": 8.0,
                "source_url": "https://poll.qu.edu/poll-release?releaseid=3948",
                "results": {"Josh Shapiro": 55.0, "Stacy Garrity": 37.0},
            }
        ]

    def wikipedia_fetcher(candidates):
        return [
            {
                "pollster": "Quinnipiac University",
                "sponsor": None,
                "field_start_date": "2026-02-19",
                "field_end_date": "2026-02-23",
                "release_date": "2026-02-26",  # even a slightly different release date
                "sample_size": 836,
                "population": "RV",
                "margin_of_error": 4.7,
                "undecided_pct": 8.0,
                "source_url": "https://en.wikipedia.org/wiki/2026_Pennsylvania_gubernatorial_election",
                "results": {"Josh Shapiro": 55.0, "Stacy Garrity": 37.0},
            }
        ]

    first_count = ingest_polls(db_session, race, race_seed, fetcher=seed_fetcher)
    second_count = ingest_polls(db_session, race, race_seed, fetcher=wikipedia_fetcher)

    assert first_count == 1
    assert second_count == 0  # same pollster + field dates -> not a duplicate


def test_polls_are_scoped_per_race(db_session, tables):
    race_a = make_race(db_session, "pa")
    race_b = Race(
        state_code="oh",
        state_name="Ohio",
        office="Governor",
        election_date=date(2026, 11, 3),
        wikipedia_page_title="2026_Ohio_gubernatorial_election",
    )
    db_session.add(race_b)
    db_session.commit()

    seed_a = {
        "candidates": [{"name": "Josh Shapiro", "party": "Democratic", "incumbent": True}],
        "raw_polls": [],
    }
    seed_b = {
        "candidates": [{"name": "Vivek Ramaswamy", "party": "Republican", "incumbent": False}],
        "raw_polls": [],
    }

    def make_fetcher(pollster):
        def fetcher(candidates):
            return [
                {
                    "pollster": pollster,
                    "sponsor": None,
                    "field_start_date": "2026-02-19",
                    "field_end_date": "2026-02-23",
                    "release_date": "2026-02-25",
                    "sample_size": 800,
                    "population": "RV",
                    "margin_of_error": 4.0,
                    "undecided_pct": 50.0,
                    "source_url": "https://example.com",
                    "results": {next(iter(candidates)): 50.0},
                }
            ]

        return fetcher

    ingest_polls(db_session, race_a, seed_a, fetcher=make_fetcher("Pollster A"))
    ingest_polls(db_session, race_b, seed_b, fetcher=make_fetcher("Pollster B"))

    from app.models import Poll

    a_polls = db_session.query(Poll).filter(Poll.race_id == race_a.id).all()
    b_polls = db_session.query(Poll).filter(Poll.race_id == race_b.id).all()
    assert len(a_polls) == 1
    assert len(b_polls) == 1
    assert a_polls[0].pollster == "Pollster A"
    assert b_polls[0].pollster == "Pollster B"


def test_fetch_live_polls_maps_surnames_to_full_candidate_names(db_session, tables):
    shapiro = Candidate(id=1, name="Josh Shapiro", party="Democratic", incumbent=True)
    garrity = Candidate(id=2, name="Stacy Garrity", party="Republican", incumbent=False)
    candidates = {"Josh Shapiro": shapiro, "Stacy Garrity": garrity}

    scraped = [
        ScrapedPoll(
            pollster="Test Pollster",
            field_start_date=date(2026, 6, 1),
            field_end_date=date(2026, 6, 3),
            release_date=date(2026, 6, 5),
            sample_size=500,
            population="RV",
            margin_of_error=4.0,
            undecided_pct=10.0,
            source_url="https://en.wikipedia.org/wiki/x",
            results={"Josh Shapiro": 52.0, "Stacy Garrity": 38.0},
        )
    ]

    with patch(
        "app.ingestion.pipeline.fetch_general_election_polls", return_value=scraped
    ) as mock_fetch:
        raw = fetch_live_polls(candidates, "2026_Pennsylvania_gubernatorial_election")

    call_args = mock_fetch.call_args[0]
    assert call_args[0] == "2026_Pennsylvania_gubernatorial_election"
    assert call_args[1] == {"Shapiro": "Josh Shapiro", "Garrity": "Stacy Garrity"}
    assert raw[0]["pollster"] == "Test Pollster"
    assert raw[0]["results"] == {"Josh Shapiro": 52.0, "Stacy Garrity": 38.0}


def test_get_or_create_candidates_backfills_kalshi_ticker_and_photo_url_onto_existing_rows(
    db_session, tables
):
    # Simulates the real workflow: a race is already deployed (candidate
    # exists with no ticker), then a ticker is added to seed_data.py later
    # -- get_or_create_candidates must pick it up on the next call rather
    # than only ever creating brand-new candidates.
    race = make_race(db_session)
    race_seed = {
        "candidates": [{"name": "Josh Shapiro", "party": "Democratic", "incumbent": True}],
        "raw_polls": [],
    }
    get_or_create_candidates(db_session, race, race_seed)

    shapiro = db_session.query(Candidate).filter(Candidate.name == "Josh Shapiro").first()
    assert shapiro.kalshi_ticker is None
    assert shapiro.photo_url is None

    updated_seed = {
        "candidates": [
            {
                "name": "Josh Shapiro",
                "party": "Democratic",
                "incumbent": True,
                "kalshi_ticker": "KXGOVPA-26-SHAP",
                "photo_url": "https://example.com/shapiro.jpg",
            }
        ],
        "raw_polls": [],
    }
    get_or_create_candidates(db_session, race, updated_seed)

    db_session.refresh(shapiro)
    assert shapiro.kalshi_ticker == "KXGOVPA-26-SHAP"
    assert shapiro.photo_url == "https://example.com/shapiro.jpg"

    all_shapiros = db_session.query(Candidate).filter(Candidate.name == "Josh Shapiro").all()
    assert len(all_shapiros) == 1  # updated in place, not duplicated


def test_get_or_create_candidates_never_syncs_party_incumbent_or_name(db_session, tables):
    # party/incumbent feed the forecasting model -- silently changing them
    # on a restart could shift historical forecasts' meaning without an
    # explicit acknowledgment, unlike the purely-additive fields above.
    race = make_race(db_session)
    race_seed = {
        "candidates": [{"name": "Josh Shapiro", "party": "Democratic", "incumbent": True}],
        "raw_polls": [],
    }
    get_or_create_candidates(db_session, race, race_seed)

    conflicting_seed = {
        "candidates": [{"name": "Josh Shapiro", "party": "Republican", "incumbent": False}],
        "raw_polls": [],
    }
    get_or_create_candidates(db_session, race, conflicting_seed)

    shapiro = db_session.query(Candidate).filter(Candidate.name == "Josh Shapiro").first()
    assert shapiro.party == "Democratic"
    assert shapiro.incumbent is True
