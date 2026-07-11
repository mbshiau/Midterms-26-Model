"""Poll collection pipeline: Scheduler -> Fetcher -> Parser -> Validation -> DB.

Two fetchers share the same parse/validate/persist stages below:
- `fetch_raw_polls` (default): the curated seed dataset, used to guarantee a
  reliable baseline at startup even if the network is unavailable.
- `fetch_live_polls`: a real scraper against Wikipedia's polling table (see
  app.ingestion.wikipedia_scraper), used by the scheduled 24h refresh job to
  pick up newly-added polls.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.ingestion.wikipedia_scraper import fetch_general_election_polls
from app.models import Candidate, Poll, PollResult, Population
from app.seed.seed_data import CANDIDATES, RAW_POLLS

logger = logging.getLogger(__name__)

WIKIPEDIA_PAGE_TITLE = "2026_Pennsylvania_gubernatorial_election"


class PollValidationError(ValueError):
    pass


def fetch_raw_polls(candidates: dict[str, Candidate] | None = None) -> list[dict]:
    """Fetcher stage (baseline). Returns the curated seed poll records."""
    return RAW_POLLS


def fetch_live_polls(candidates: dict[str, Candidate]) -> list[dict]:
    """Fetcher stage (live). Scrapes Wikipedia's polling table for any polls
    not already in `candidates`' seed data. Returns [] on any failure —
    network errors or an unexpected page structure should never crash the
    scheduled job, just leave the poll set unchanged until the next run."""
    surname_to_name = {name.split()[-1]: name for name in candidates}
    scraped = fetch_general_election_polls(WIKIPEDIA_PAGE_TITLE, surname_to_name)

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


def get_or_create_candidates(db: Session) -> dict[str, Candidate]:
    by_name = {c.name: c for c in db.query(Candidate).all()}
    for c in CANDIDATES:
        if c["name"] not in by_name:
            candidate = Candidate(**c)
            db.add(candidate)
            db.flush()
            by_name[c["name"]] = candidate
    db.commit()
    return by_name


def _poll_exists(db: Session, parsed: dict) -> bool:
    """A poll is identified by pollster + field dates alone (not source_url):
    the same poll can legitimately be cited via different URLs — a curated
    press release for the seed data vs. the Wikipedia aggregator page the
    live scraper always cites — and that must never produce a duplicate."""
    return (
        db.query(Poll)
        .filter(
            Poll.pollster == parsed["pollster"],
            Poll.field_start_date == parsed["field_start_date"],
            Poll.field_end_date == parsed["field_end_date"],
        )
        .first()
        is not None
    )


def ingest_polls(db: Session, fetcher=fetch_raw_polls) -> int:
    """Runs the full pipeline and persists new polls. Returns count ingested.

    Individual malformed rows (parse/validation failures) are skipped and
    logged rather than aborting the whole run — important for `fetch_live_polls`,
    where one badly-formatted row on Wikipedia shouldn't block the rest.
    """
    candidates = get_or_create_candidates(db)
    ingested = 0

    for raw in fetcher(candidates):
        try:
            parsed = parse_raw_poll(raw)
            validate_poll(parsed)
        except (PollValidationError, KeyError, ValueError) as e:
            logger.warning("skipping malformed poll record %r: %s", raw.get("pollster"), e)
            continue

        if _poll_exists(db, parsed):
            continue

        unknown = [name for name in parsed["results"] if name not in candidates]
        if unknown:
            logger.warning("skipping poll with unknown candidate(s) %s: %r", unknown, parsed["pollster"])
            continue

        poll = Poll(
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
