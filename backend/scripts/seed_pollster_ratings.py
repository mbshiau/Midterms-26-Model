"""One-time seed for the pollster_ratings table.

Unlike presidential approval and the generic congressional ballot -- current-
opinion snapshots that genuinely move day to day, refreshed on the scheduled
job -- a pollster's historical average error (see
app.services.pollster_ratings) only changes when a new election cycle's
results are certified, at most a few times a year. So this is run by hand
when you actually want to refresh it, not on every app startup or as part of
the twice-daily scheduled job.

Usage (from inside the backend container or a matching venv):
    python -m scripts.seed_pollster_ratings
"""

import logging

from app import database
from app.ingestion.pollster_ratings_scraper import fetch_pollster_ratings
from app.services.pollster_ratings import upsert_pollster_ratings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = database.SessionLocal()
    try:
        scraped = fetch_pollster_ratings()
        if not scraped:
            logger.warning("pollster ratings scrape returned no rows -- table left unchanged")
            return
        count = upsert_pollster_ratings(db, scraped)
        logger.info("seeded %d pollster ratings", count)
    finally:
        db.close()


if __name__ == "__main__":
    main()
