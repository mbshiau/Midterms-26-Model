"""Scheduler stage: refreshes polls (per race) + presidential approval and
the generic congressional ballot (national, once each) + Kalshi market odds
(per candidate with a configured ticker) and regenerates every race's
forecast, entirely in the background, at fixed wall-clock times every day.

Pollster quality ratings (see app.services.pollster_ratings) are
deliberately NOT part of this recurring refresh -- unlike approval/generic
ballot, which are current-opinion snapshots that genuinely move day to day,
a pollster's historical average error only changes when a new election
cycle's results are certified (at most a few times a year), so it's scraped
once as a one-time seed rather than re-scraped on a schedule.

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
from app.ingestion.generic_ballot_scraper import fetch_current_generic_ballot
from app.ingestion.kalshi_scraper import fetch_market_odds
from app.ingestion.pipeline import fetch_live_polls, ingest_polls
from app.models import Candidate, Race
from app.services.approval import update_approval
from app.services.forecasting import generate_forecast
from app.services.generic_ballot import update_generic_ballot
from app.services.market_odds import update_market_odds
from app.services.races import get_race_seed

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Refresh at noon and 7pm, US Eastern time (handles EST/EDT automatically).
REFRESH_HOURS = "12,19"
REFRESH_TIMEZONE = "America/New_York"

# APScheduler's default misfire_grace_time is 1 second: if the background
# thread's check of a due job is delayed past that (e.g. the process was busy
# holding the GIL running CPU-bound Monte Carlo simulations for a burst of
# forecast requests), the run is silently skipped entirely and pushed to the
# *next* scheduled slot -- up to 7 hours later -- rather than just running
# late. A generous grace window means a delayed check still fires instead of
# vanishing.
MISFIRE_GRACE_SECONDS = 3600


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

        scraped_ballot = fetch_current_generic_ballot()
        if scraped_ballot is not None:
            update_generic_ballot(db, scraped_ballot)
            logger.info(
                "scheduled refresh: generic ballot now Dem %.1f%% / Rep %.1f%% (as of %s)",
                scraped_ballot.dem_pct, scraped_ballot.rep_pct, scraped_ballot.as_of,
            )
        else:
            logger.warning("scheduled refresh: generic ballot scrape failed, keeping previous value")

        races = db.query(Race).all()
        for race in races:
            # Each race is isolated: a scraping quirk in one state's
            # Wikipedia table or a Kalshi hiccup must never abort the loop
            # and silently skip every remaining state's refresh (which is
            # exactly what an exception here used to do, since this used to
            # be one try/except around the whole loop instead of per-race).
            try:
                race_seed = get_race_seed(race.state_code)
                live_fetcher = partial(
                    fetch_live_polls, wikipedia_page_title=race_seed["wikipedia_page_title"]
                )
                new_poll_count = ingest_polls(db, race, race_seed, fetcher=live_fetcher)
                logger.info(
                    "scheduled refresh: %s — %d new poll(s) from Wikipedia",
                    race.state_code, new_poll_count,
                )

                candidates_with_tickers = (
                    db.query(Candidate)
                    .filter(Candidate.race_id == race.id, Candidate.kalshi_ticker.isnot(None))
                    .all()
                )
                for candidate in candidates_with_tickers:
                    scraped = fetch_market_odds(candidate.kalshi_ticker)
                    if scraped is None:
                        logger.warning(
                            "scheduled refresh: %s — Kalshi fetch failed for %s (%s)",
                            race.state_code, candidate.name, candidate.kalshi_ticker,
                        )
                        continue
                    update_market_odds(db, candidate.id, scraped)
                    logger.info(
                        "scheduled refresh: %s — Kalshi odds for %s now %.1f%%",
                        race.state_code, candidate.name, scraped.yes_price_pct,
                    )

                generate_forecast(db, race)
                logger.info("scheduled refresh: %s forecast regenerated", race.state_code)
            except Exception:
                logger.exception("scheduled refresh: %s failed, continuing with remaining races", race.state_code)
                db.rollback()
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
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
