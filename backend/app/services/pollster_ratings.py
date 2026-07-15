"""Reads/writes PollsterRating rows and computes the quality-weight
multiplier that app.services.weighting.poll_weight applies on top of its
existing recency x sample-size weighting.

Unlike PresidentApproval/GenericBallot (a single upserted row), this is a
whole table -- one row per pollster, refreshed by upserting every scraped
row on each scheduled run (see app.ingestion.pollster_ratings_scraper).
"""

from sqlalchemy.orm import Session

from app.config import settings
from app.ingestion.pollster_ratings_scraper import ScrapedPollsterRating
from app.models import PollsterRating


def normalize_pollster_name(name: str) -> str:
    """Matches Poll.pollster (our own stored name) against a scraped
    PollsterRating's name -- lowercased/stripped exact match only, no fuzzy
    matching. A pollster with no match just gets a neutral quality weight
    (see pollster_quality_weight), not an error."""
    return name.strip().lower()


def get_pollster_ratings_by_name(db: Session) -> dict[str, PollsterRating]:
    rows = db.query(PollsterRating).all()
    return {row.normalized_name: row for row in rows}


def upsert_pollster_ratings(db: Session, scraped: list[ScrapedPollsterRating]) -> int:
    """Upserts every scraped row by normalized name. Returns count processed."""
    existing = {row.normalized_name: row for row in db.query(PollsterRating).all()}
    processed = 0

    for item in scraped:
        key = normalize_pollster_name(item.pollster)
        row = existing.get(key)
        if row is None:
            row = PollsterRating(pollster_name=item.pollster, normalized_name=key, source_url=item.source_url)
            db.add(row)
            existing[key] = row

        row.pollster_name = item.pollster
        row.avg_error_pts = item.avg_error_pts
        row.lean_party = item.lean_party
        row.lean_pts = item.lean_pts
        row.winner_called_pct = item.winner_called_pct
        row.polls_count = item.polls_count
        row.cycles_count = item.cycles_count
        row.source_url = item.source_url
        processed += 1

    db.commit()
    return processed


def pollster_quality_weight(avg_error_pts: float | None) -> float:
    """Neutral 1.0 when there's no error figure to go on (an untracked
    pollster, or a tracked one with too few polls for PollingSource to
    compute an average yet) -- absence of data is never treated as bad data."""
    if avg_error_pts is None or avg_error_pts <= 0:
        return 1.0

    raw = settings.pollster_baseline_error_pts / avg_error_pts
    return min(max(raw, settings.pollster_quality_weight_floor), settings.pollster_quality_weight_ceiling)
