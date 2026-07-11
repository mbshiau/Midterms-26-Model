from unittest.mock import patch

import pytest

from app.database import Base
from app.ingestion.pipeline import fetch_live_polls, ingest_polls
from app.ingestion.wikipedia_scraper import ScrapedPoll
from datetime import date


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


def test_same_poll_cited_via_different_url_is_not_duplicated(db_session, tables):
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

    from app.models import Candidate

    db_session.add_all(
        [
            Candidate(name="Josh Shapiro", party="Democratic", incumbent=True),
            Candidate(name="Stacy Garrity", party="Republican", incumbent=False),
        ]
    )
    db_session.commit()

    first_count = ingest_polls(db_session, fetcher=seed_fetcher)
    second_count = ingest_polls(db_session, fetcher=wikipedia_fetcher)

    assert first_count == 1
    assert second_count == 0  # same pollster + field dates -> not a duplicate


def test_fetch_live_polls_maps_surnames_to_full_candidate_names(db_session, tables):
    from app.models import Candidate

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
        raw = fetch_live_polls(candidates)

    call_args = mock_fetch.call_args[0]
    assert call_args[1] == {"Shapiro": "Josh Shapiro", "Garrity": "Stacy Garrity"}
    assert raw[0]["pollster"] == "Test Pollster"
    assert raw[0]["results"] == {"Josh Shapiro": 52.0, "Stacy Garrity": 38.0}
