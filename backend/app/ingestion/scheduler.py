"""Scheduler stage: periodically refreshes polls (per race) + presidential
approval (national, once) and regenerates every race's forecast, entirely
in the background.

`add_job` is given an explicit `next_run_time` (now + interval) rather than
leaving it at the default: APScheduler's default next_run_time is "now",
which would fire immediately and duplicate the synchronous startup run in
app.main's lifespan. An earlier version of this file passed
`next_run_time=None`, which actually *disables* the job entirely (it's
added but never fires again) — worth calling out since it's a one-character
difference between "runs every 24h" and "never runs."
"""

import logging
from datetime import datetime, timedelta
from functools import partial

from apscheduler.schedulers.background import BackgroundScheduler

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


def start_scheduler(interval_hours: int = 24) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_refresh_job,
        "interval",
        hours=interval_hours,
        next_run_time=datetime.now() + timedelta(hours=interval_hours),
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
