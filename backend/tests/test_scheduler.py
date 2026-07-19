from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from app.ingestion import scheduler
from app.ingestion.news_scraper import ScrapedNewsArticle
from app.models import Candidate, NewsArticle, Race
from app.services.forecasting import forecast_history
from app.services.news import get_recent_news


def test_start_scheduler_sets_a_real_next_run_time():
    sched = scheduler.start_scheduler()
    try:
        jobs = sched.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].next_run_time is not None
    finally:
        scheduler.stop_scheduler()


def test_start_scheduler_is_idempotent():
    first = scheduler.start_scheduler()
    second = scheduler.start_scheduler()
    try:
        assert first is second
    finally:
        scheduler.stop_scheduler()


def test_misfire_grace_time_is_generous_not_the_apscheduler_default():
    # Regression test: APScheduler's default misfire_grace_time is 1 second.
    # If the background thread's check of a due job is delayed past that --
    # e.g. by a burst of CPU-bound forecast/simulation requests holding the
    # GIL -- the run is silently skipped and pushed to the next scheduled
    # slot (up to 7 hours later) instead of just running late. This is
    # exactly what happened in production: the 7pm refresh never fired
    # because the process was busy serving forecast requests.
    sched = scheduler.start_scheduler()
    try:
        job = sched.get_jobs()[0]
        assert job.misfire_grace_time is not None
        assert job.misfire_grace_time >= 300
    finally:
        scheduler.stop_scheduler()


def test_one_races_scraping_failure_does_not_block_other_races(client, db_session):
    # Regression test for a real production incident: a ragged Wikipedia
    # table row crashed with an IndexError while parsing California's polls,
    # and because the whole per-race loop was wrapped in a single
    # try/except, every state processed after California in that run never
    # got its poll refresh, Kalshi refresh, or forecast regeneration --
    # silently, with no visible error to the end user. One race's failure
    # must never block any other race.
    def flaky_ingest_polls(db, race, race_seed, fetcher=None):
        if race.state_code == "pa":
            raise IndexError("simulated ragged Wikipedia row")
        return 0

    races = {r.state_code: r for r in db_session.query(Race).all()}
    other_codes = [code for code in ("oh", "ca", "tx") if code in races]
    snapshots_before = {code: len(forecast_history(db_session, races[code])) for code in other_codes}
    pa_snapshots_before = len(forecast_history(db_session, races["pa"]))

    with (
        patch("app.ingestion.scheduler.fetch_current_approval", return_value=None),
        patch("app.ingestion.scheduler.ingest_polls", side_effect=flaky_ingest_polls),
        patch("app.ingestion.scheduler.fetch_market_odds", return_value=None),
        patch("app.ingestion.scheduler.fetch_race_news", return_value=[]),
    ):
        scheduler._run_refresh_job()

    # PA itself crashed before reaching generate_forecast -- no new snapshot.
    assert len(forecast_history(db_session, races["pa"])) == pa_snapshots_before

    # Every other race still got refreshed, regardless of iteration order
    # relative to PA.
    for code in other_codes:
        assert len(forecast_history(db_session, races[code])) == snapshots_before[code] + 1


def test_refresh_race_intelligence_generates_relevance_only_for_new_articles(monkeypatch, client, db_session):
    from app.config import settings

    monkeypatch.setattr(settings, "uf_navigator_api_key", "test-key")

    race = db_session.query(Race).filter(Race.state_code == "pa").first()
    candidates = db_session.query(Candidate).filter(Candidate.race_id == race.id).all()

    already_summarized = NewsArticle(
        race_id=race.id,
        headline="Already summarized",
        source="Example",
        url="https://example.com/existing",
        published_at=datetime.now(timezone.utc),
        ai_relevance="Existing blurb -- must not be overwritten.",
    )
    db_session.add(already_summarized)
    db_session.commit()

    scraped = [
        ScrapedNewsArticle(
            headline="Already summarized",
            source="Example",
            url="https://example.com/existing",
            published_at=datetime.now(timezone.utc),
        ),
        ScrapedNewsArticle(
            headline="Brand new headline",
            source="Example",
            url="https://example.com/new",
            published_at=datetime.now(timezone.utc),
        ),
    ]

    fake_client = MagicMock()
    fake_choice = MagicMock()
    fake_choice.message.content = "Freshly generated blurb."
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    fake_client.chat.completions.create.return_value = fake_response

    with (
        patch("app.ingestion.scheduler.fetch_race_news", return_value=scraped),
        patch("app.services.ai_summary._client", return_value=fake_client),
    ):
        scheduler.refresh_race_intelligence(db_session, race, candidates)

    articles = {a.url: a for a in get_recent_news(db_session, race.id)}
    assert articles["https://example.com/existing"].ai_relevance == "Existing blurb -- must not be overwritten."
    assert articles["https://example.com/new"].ai_relevance == "Freshly generated blurb."
    # Only the new article needed an AI call -- the existing one already had a blurb.
    assert fake_client.chat.completions.create.call_count == 1


def test_next_run_lands_on_noon_or_7pm_eastern():
    # Regression test for the interval-trigger bug where the "next run" was
    # computed as now + 24h at registration time, so it silently reset every
    # time the process restarted. A cron trigger must instead always land on
    # a fixed wall-clock time (noon or 7pm Eastern), independent of exactly
    # when start_scheduler() was called.
    sched = scheduler.start_scheduler()
    try:
        next_run = sched.get_jobs()[0].next_run_time
        eastern_time = next_run.astimezone(ZoneInfo("America/New_York"))
        assert (eastern_time.hour, eastern_time.minute) in {(12, 0), (19, 0)}
    finally:
        scheduler.stop_scheduler()
