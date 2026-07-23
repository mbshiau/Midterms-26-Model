"""Scheduler stage: two independent recurring jobs, entirely in the
background, at fixed wall-clock times every day.

- Market/intel refresh (hourly): Kalshi market odds (per candidate with a
  configured ticker) + each race's news scrape and AI Race Intelligence
  summary. These genuinely move within a day and are cheap to check, so they
  run every hour -- see refresh_race_intelligence's docstring for how the AI
  summary call itself is still gated on whether a new headline came in, so
  hourly checking doesn't mean hourly AI billing.
- Forecast refresh (noon and 7pm): presidential approval + the generic
  congressional ballot (national, once each), each race's poll scrape, and
  the actual Monte Carlo forecast regeneration. These are kept off the
  hourly cadence deliberately -- a poll release or a shift in national
  approval is a real, infrequent event, and regenerating every race's
  forecast snapshot every single hour regardless of whether anything new
  came in would bloat forecast history with duplicate snapshots for no
  reason (forecast history is meant to reflect real refresh events, not
  clock ticks).

Pollster quality ratings (see app.services.pollster_ratings) are
deliberately NOT part of either recurring refresh -- unlike approval/generic
ballot, which are current-opinion snapshots that genuinely move day to day,
a pollster's historical average error only changes when a new election
cycle's results are certified (at most a few times a year), so it's scraped
once as a one-time seed rather than re-scraped on a schedule.

Both jobs use a cron trigger (fixed times of day) rather than an interval
trigger (fixed delay from whenever the job was registered). An interval
trigger's "next run" is computed as `now + interval` at scheduler startup, so
it silently resets every time the process restarts — including restarts
that have nothing to do with a real refresh event (e.g. adding a new
state's seed data). A cron trigger instead computes its next fire time from
the clock itself, so it lands on the same wall-clock times regardless of how
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
from app.ingestion.news_scraper import build_news_query, fetch_race_news, filter_relevant_articles
from app.ingestion.pipeline import fetch_live_polls, ingest_polls
from app.models import Candidate, Race
from app.services.ai_summary import (
    generate_article_relevance,
    generate_market_analysis,
    update_race_intelligence,
)
from app.services.approval import update_approval
from app.services.forecasting import generate_forecast, latest_forecast
from app.services.generic_ballot import update_generic_ballot
from app.services.market_odds import get_market_odds, update_market_odds
from app.services.news import get_recent_news, purge_irrelevant_articles, update_news
from app.services.races import get_race_seed

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Forecast refresh: noon and 7pm, US Eastern time (handles EST/EDT
# automatically -- see module docstring on cron vs. interval trigger).
FORECAST_REFRESH_HOURS = "12,19"
REFRESH_TIMEZONE = "America/New_York"

# APScheduler's default misfire_grace_time is 1 second: if the background
# thread's check of a due job is delayed past that (e.g. the process was busy
# holding the GIL running CPU-bound Monte Carlo simulations for a burst of
# forecast requests), the run is silently skipped entirely and pushed to the
# *next* scheduled slot -- up to 7 hours later for the forecast job -- rather
# than just running late. A generous grace window means a delayed check
# still fires instead of vanishing.
FORECAST_MISFIRE_GRACE_SECONDS = 3600

# The market/intel job is hourly, so its own slot is only 1 hour away --
# a smaller grace window is enough to absorb a delayed check without risking
# overlap with the next scheduled run.
INTEL_MISFIRE_GRACE_SECONDS = 900


def refresh_race_intelligence(db, race: Race, candidates: list[Candidate]) -> None:
    """News + AI-summary step for one race's Race Intelligence section (see
    app.services.news / app.services.ai_summary), called from the scheduled
    refresh below.

    Deliberately does not raise -- callers wrap this in their own
    try/except so a news-scrape or AI-provider hiccup here never prevents
    that race's forecast (the actually load-bearing output) from
    regenerating."""
    other_state_names = [r.state_name for r in db.query(Race).filter(Race.id != race.id).all()]

    scraped_news = fetch_race_news(build_news_query(race.state_name, race.office))
    scraped_news = filter_relevant_articles(scraped_news, race.state_name, other_state_names)
    new_count = update_news(db, race.id, scraped_news)
    if new_count:
        logger.info("scheduled refresh: %s — %d new headline(s)", race.slug, new_count)

    # Also re-validate whatever's already stored -- filtering the fresh
    # scrape above only stops *new* contamination; rows saved before this
    # filter existed (or before it was tightened) stay until something
    # actively re-checks them (see purge_irrelevant_articles).
    purged = purge_irrelevant_articles(db, race.id, race.state_name, other_state_names)
    if purged:
        logger.info("scheduled refresh: %s — purged %d irrelevant headline(s)", race.slug, purged)

    articles = get_recent_news(db, race.id)

    # Per-article relevance blurb is generated once and cached (see
    # NewsArticle.ai_relevance) -- only for articles that don't have one yet,
    # so an unchanged headline isn't re-summarized (and re-billed) on every
    # refresh, just newly-scraped ones.
    for article in articles:
        if article.ai_relevance is None:
            relevance = generate_article_relevance(race, article)
            if relevance is not None:
                article.ai_relevance = relevance
    db.commit()

    # The AI market-analysis blurb is only regenerated when a new headline
    # actually came in this run -- with the refresh now hourly, calling the
    # AI provider every single run regardless would be ~24x/day of billing
    # for a summary that most hours has nothing new to say. Passing None
    # leaves the previously-cached analysis in place (see
    # update_race_intelligence's docstring) rather than blanking it.
    market_analysis = None
    if new_count:
        candidates_by_id = {c.id: c for c in candidates}
        kalshi_rows = list(get_market_odds(db, [c.id for c in candidates]).values())
        snapshot = latest_forecast(db, race)
        market_analysis = generate_market_analysis(race, snapshot, kalshi_rows, candidates_by_id)

    update_race_intelligence(db, race.id, market_analysis)


def _run_market_intel_refresh_job() -> None:
    """Hourly job: Kalshi odds + news/AI Race Intelligence, per race. Never
    touches polls or the forecast -- see module docstring."""
    db = database.SessionLocal()
    try:
        races = db.query(Race).all()
        for race in races:
            # Each race is isolated: a Kalshi hiccup or news-scrape quirk in
            # one state must never abort the loop and silently skip every
            # remaining state's refresh.
            try:
                candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
                candidates_with_tickers = [c for c in candidates if c.kalshi_ticker is not None]
                for candidate in candidates_with_tickers:
                    scraped = fetch_market_odds(candidate.kalshi_ticker)
                    if scraped is None:
                        logger.warning(
                            "scheduled market/intel refresh: %s — Kalshi fetch failed for %s (%s)",
                            race.slug, candidate.name, candidate.kalshi_ticker,
                        )
                        continue
                    update_market_odds(db, candidate.id, scraped)
                    logger.info(
                        "scheduled market/intel refresh: %s — Kalshi odds for %s now %.1f%%",
                        race.slug, candidate.name, scraped.yes_price_pct,
                    )

                refresh_race_intelligence(db, race, candidates)
                logger.info("scheduled market/intel refresh: %s race intelligence updated", race.slug)
            except Exception:
                # rollback() before touching `race` again below is required,
                # not optional -- a failed flush leaves the session's
                # transaction dead, and `race.slug` lazy-loads `race.office`,
                # which would raise PendingRollbackError against a dead
                # transaction instead of just logging and continuing.
                db.rollback()
                logger.exception(
                    "scheduled market/intel refresh: %s failed, continuing with remaining races", race.slug
                )
    except Exception:
        logger.exception("scheduled market/intel refresh job failed")
    finally:
        db.close()


def _run_forecast_refresh_job() -> None:
    """Noon/7pm job: national approval + generic ballot, each race's poll
    scrape, and forecast regeneration."""
    db = database.SessionLocal()
    try:
        scraped_approval = fetch_current_approval()
        if scraped_approval is not None:
            update_approval(db, scraped_approval, party=PRESIDENT["party"], name=PRESIDENT["name"])
            logger.info(
                "scheduled forecast refresh: approval now %.1f%% (as of %s)",
                scraped_approval.approval_pct,
                scraped_approval.as_of,
            )
        else:
            logger.warning("scheduled forecast refresh: approval scrape failed, keeping previous value")

        scraped_ballot = fetch_current_generic_ballot()
        if scraped_ballot is not None:
            update_generic_ballot(db, scraped_ballot)
            logger.info(
                "scheduled forecast refresh: generic ballot now Dem %.1f%% / Rep %.1f%% (as of %s)",
                scraped_ballot.dem_pct, scraped_ballot.rep_pct, scraped_ballot.as_of,
            )
        else:
            logger.warning("scheduled forecast refresh: generic ballot scrape failed, keeping previous value")

        races = db.query(Race).all()
        for race in races:
            # Each race is isolated: a scraping quirk in one state's
            # Wikipedia table must never abort the loop and silently skip
            # every remaining state's refresh.
            try:
                race_seed = get_race_seed(race.slug)
                live_fetcher = partial(
                    fetch_live_polls, wikipedia_page_title=race_seed["wikipedia_page_title"]
                )
                new_poll_count = ingest_polls(db, race, race_seed, fetcher=live_fetcher)
                logger.info(
                    "scheduled forecast refresh: %s — %d new poll(s) from Wikipedia",
                    race.slug, new_poll_count,
                )

                generate_forecast(db, race)
                logger.info("scheduled forecast refresh: %s forecast regenerated", race.slug)
            except Exception:
                db.rollback()
                logger.exception(
                    "scheduled forecast refresh: %s failed, continuing with remaining races", race.slug
                )
    except Exception:
        logger.exception("scheduled forecast refresh job failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_market_intel_refresh_job,
        CronTrigger(minute=0, timezone=REFRESH_TIMEZONE),
        misfire_grace_time=INTEL_MISFIRE_GRACE_SECONDS,
    )
    _scheduler.add_job(
        _run_forecast_refresh_job,
        # Offset 5 minutes past the hour so noon/7pm don't fire in the same
        # instant as the hourly market/intel job above.
        CronTrigger(hour=FORECAST_REFRESH_HOURS, minute=5, timezone=REFRESH_TIMEZONE),
        misfire_grace_time=FORECAST_MISFIRE_GRACE_SECONDS,
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
