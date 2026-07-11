from app.ingestion import scheduler


def test_start_scheduler_sets_a_real_next_run_time():
    """Regression test for a bug where next_run_time=None silently disabled
    the job forever instead of scheduling it for one interval out."""
    sched = scheduler.start_scheduler(interval_hours=24)
    try:
        jobs = sched.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].next_run_time is not None
    finally:
        scheduler.stop_scheduler()


def test_start_scheduler_is_idempotent():
    first = scheduler.start_scheduler(interval_hours=24)
    second = scheduler.start_scheduler(interval_hours=24)
    try:
        assert first is second
    finally:
        scheduler.stop_scheduler()
