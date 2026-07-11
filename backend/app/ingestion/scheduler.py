"""Scheduler stage: refreshes polls (per race) + presidential approval
(national, once) and regenerates every race's forecast, entirely in the
background, at fixed wall-clock times every day.

Uses a cron trigger (fixed times of day) rather than an interval trigger
(fixed delay from whenever the job was registered). An interval trigger's
"next run" is computed as `now + interval` at scheduler startup, so it
silently resets every time the process restarts — including restarts that
have nothing to do with a real refresh event (e.g. adding a new state's
seed data). A cron trigger instead computes its next fire time from the
clock itself, so it lands on the same wall-clock times regardless of how
many times the container has restarted in between.
"""

import logging
from functools import partial

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import database
from app.data.fundamentals_data import PRESIDENT
from app.ingestion.approval_scraper import fetch_current_approval
from app.ingestion.pipeline import fetch_live_polls, ingest_polls
from app.models import Race
from app.services.approval import update_approval
from app.services.forecasting import generate_forecast
from app.services.races import get_race_seed

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Refresh at noon and 7pm, US Eastern time (handles EST/EDT automatically).
REFRESH_HOURS = "12,19"
REFRESH_TIMEZONE = "America/New_York"


def _run_refresh_job() -> None:
    db = database.SessionLocal()
    try:
        scraped_approval = fetch_current_approval()
        if scraped_approval is not None:
            update_approval(db, scraped_approval, party=PRESIDENT["party"], name=PRESIDENT["name"])
            logger.info(
                "scheduled refresh: approval now %.1f%% (as of %s)",
                scraped_approval.approval_pct,
                scraped_approval.as_of,
            )
        else:
            logger.warning("scheduled refresh: approval scrape failed, keeping previous value")

        races = db.query(Race).all()
        for race in races:
            race_seed = get_race_seed(race.state_code)
            live_fetcher = partial(
                fetch_live_polls, wikipedia_page_title=race_seed["wikipedia_page_title"]
            )
            new_poll_count = ingest_polls(db, race, race_seed, fetcher=live_fetcher)
            logger.info(
                "scheduled refresh: %s — %d new poll(s) from Wikipedia",
                race.state_code, new_poll_count,
            )
            generate_forecast(db, race)
            logger.info("scheduled refresh: %s forecast regenerated", race.state_code)
    except Exception:
        logger.exception("scheduled refresh job failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_refresh_job,
        CronTrigger(hour=REFRESH_HOURS, minute=0, timezone=REFRESH_TIMEZONE),
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
