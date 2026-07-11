"""Poll collection pipeline: Scheduler -> Fetcher -> Parser -> Validation -> DB.

Everything here is scoped to a single Race. Two fetchers share the same
parse/validate/persist stages below:
- `fetch_raw_polls` (default): the curated seed dataset for that race, used
  to guarantee a reliable baseline at startup even if the network is down.
- `fetch_live_polls`: a real scraper against that race's Wikipedia polling
  table (see app.ingestion.wikipedia_scraper), used by the scheduled 24h
  refresh job to pick up newly-added polls.
"""

import logging
from datetime import date
from typing import Callable

from sqlalchemy.orm import Session

from app.ingestion.wikipedia_scraper import fetch_general_election_polls
from app.models import Candidate, Poll, PollResult, Population, Race

logger = logging.getLogger(__name__)


class PollValidationError(ValueError):
    pass


def fetch_raw_polls(race_seed: dict, candidates: dict[str, Candidate]) -> list[dict]:
    """Fetcher stage (baseline). Returns the curated seed poll records."""
    return race_seed["raw_polls"]


def fetch_live_polls(candidates: dict[str, Candidate], wikipedia_page_title: str) -> list[dict]:
    """Fetcher stage (live). Scrapes Wikipedia's polling table for any polls
    not already known. Returns [] on any failure — network errors or an
    unexpected page structure should never crash the scheduled job, just
    leave the poll set unchanged until the next run."""
    surname_to_name = {name.split()[-1]: name for name in candidates}
    scraped = fetch_general_election_polls(wikipedia_page_title, surname_to_name)

    return [
        {
            "pollster": poll.pollster,
            "sponsor": None,
            "field_start_date": poll.field_start_date.isoformat(),
            "field_end_date": poll.field_end_date.isoformat(),
            "release_date": poll.release_date.isoformat(),
            "sample_size": poll.sample_size,
            "population": poll.population,
            "margin_of_error": poll.margin_of_error,
            "undecided_pct": poll.undecided_pct,
            "source_url": poll.source_url,
            "results": poll.results,
        }
        for poll in scraped
    ]


def parse_raw_poll(raw: dict) -> dict:
    """Parser stage. Normalizes types (dates, enums) into DB-ready fields."""
    return {
        "pollster": raw["pollster"].strip(),
        "sponsor": raw.get("sponsor"),
        "field_start_date": date.fromisoformat(raw["field_start_date"]),
        "field_end_date": date.fromisoformat(raw["field_end_date"]),
        "release_date": date.fromisoformat(raw["release_date"]),
        "sample_size": int(raw["sample_size"]),
        "population": Population(raw["population"]),
        "margin_of_error": raw.get("margin_of_error"),
        "undecided_pct": float(raw.get("undecided_pct", 0.0)),
        "source_url": raw["source_url"],
        "results": {name: float(pct) for name, pct in raw["results"].items()},
    }


def validate_poll(parsed: dict) -> None:
    """Validation stage. Raises PollValidationError on malformed records."""
    if parsed["sample_size"] <= 0:
        raise PollValidationError(f"non-positive sample size: {parsed['sample_size']}")
    if parsed["field_start_date"] > parsed["field_end_date"]:
        raise PollValidationError("field_start_date after field_end_date")
    if parsed["field_end_date"] > parsed["release_date"]:
        raise PollValidationError("field_end_date after release_date")
    if parsed["margin_of_error"] is not None and parsed["margin_of_error"] < 0:
        raise PollValidationError("negative margin of error")
    if not (0 <= parsed["undecided_pct"] <= 100):
        raise PollValidationError(f"undecided_pct out of range: {parsed['undecided_pct']}")
    total = sum(parsed["results"].values()) + parsed["undecided_pct"]
    if not (95 <= total <= 105):
        raise PollValidationError(f"candidate pcts + undecided sum to {total}, expected ~100")
    if not parsed["source_url"]:
        raise PollValidationError("missing source_url")


def get_or_create_candidates(db: Session, race: Race, race_seed: dict) -> dict[str, Candidate]:
    by_name = {
        c.name: c for c in db.query(Candidate).filter(Candidate.race_id == race.id).all()
    }
    for c in race_seed["candidates"]:
        if c["name"] not in by_name:
            candidate = Candidate(race_id=race.id, **c)
            db.add(candidate)
            db.flush()
            by_name[c["name"]] = candidate
    db.commit()
    return by_name


def _poll_exists(db: Session, race: Race, parsed: dict) -> bool:
    """A poll is identified by race + pollster + field dates (not source_url):
    the same poll can legitimately be cited via different URLs — a curated
    press release for the seed data vs. the Wikipedia aggregator page the
    live scraper always cites — and that must never produce a duplicate."""
    return (
        db.query(Poll)
        .filter(
            Poll.race_id == race.id,
            Poll.pollster == parsed["pollster"],
            Poll.field_start_date == parsed["field_start_date"],
            Poll.field_end_date == parsed["field_end_date"],
        )
        .first()
        is not None
    )


def ingest_polls(
    db: Session,
    race: Race,
    race_seed: dict,
    fetcher: Callable[[dict[str, Candidate]], list[dict]] | None = None,
) -> int:
    """Runs the full pipeline for one race and persists new polls. Returns
    count ingested.

    Individual malformed rows (parse/validation failures) are skipped and
    logged rather than aborting the whole run — important for
    `fetch_live_polls`, where one badly-formatted row on Wikipedia shouldn't
    block the rest.
    """
    fetcher = fetcher or (lambda candidates: fetch_raw_polls(race_seed, candidates))
    candidates = get_or_create_candidates(db, race, race_seed)
    ingested = 0

    for raw in fetcher(candidates):
        try:
            parsed = parse_raw_poll(raw)
            validate_poll(parsed)
        except (PollValidationError, KeyError, ValueError) as e:
            logger.warning("skipping malformed poll record %r: %s", raw.get("pollster"), e)
            continue

        if _poll_exists(db, race, parsed):
            continue

        unknown = [name for name in parsed["results"] if name not in candidates]
        if unknown:
            logger.warning("skipping poll with unknown candidate(s) %s: %r", unknown, parsed["pollster"])
            continue

        poll = Poll(
            race_id=race.id,
            pollster=parsed["pollster"],
            sponsor=parsed["sponsor"],
            field_start_date=parsed["field_start_date"],
            field_end_date=parsed["field_end_date"],
            release_date=parsed["release_date"],
            sample_size=parsed["sample_size"],
            population=parsed["population"],
            margin_of_error=parsed["margin_of_error"],
            undecided_pct=parsed["undecided_pct"],
            source_url=parsed["source_url"],
        )
        db.add(poll)
        db.flush()

        for candidate_name, pct in parsed["results"].items():
            db.add(PollResult(poll_id=poll.id, candidate_id=candidates[candidate_name].id, pct=pct))

        ingested += 1

    db.commit()
    return ingested
