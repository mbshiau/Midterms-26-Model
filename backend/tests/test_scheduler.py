from zoneinfo import ZoneInfo

from app.ingestion import scheduler


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
