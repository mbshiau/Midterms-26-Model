import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from app.config import settings
from app.ingestion.scheduler import _run_forecast_refresh_job, _run_market_intel_refresh_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _check_token(x_admin_token: str | None) -> None:
    if not settings.admin_refresh_token:
        return
    if x_admin_token != settings.admin_refresh_token:
        raise HTTPException(status_code=401, detail="invalid or missing admin token")


@router.post("/refresh/forecast")
def trigger_forecast_refresh(background_tasks: BackgroundTasks, x_admin_token: str | None = Header(default=None)):
    """Manual trigger for the noon/7pm forecast-refresh job (approval +
    generic ballot + poll scrape + Monte Carlo regen, every race).

    Exists because Render's free tier spins the service down between
    requests -- the in-process APScheduler job (app.ingestion.scheduler)
    silently misses its wall-clock slot if nothing hit the service around
    12:05/19:05 ET. An external cron (see .github/workflows) hits this
    endpoint on the same schedule instead; the request itself wakes the
    service, so there's no window for the job to be skipped.

    The actual job runs as a FastAPI background task rather than inline: the
    job can legitimately take minutes across 500+ races even with Wikipedia
    page caching (see scheduler._cached_wikipedia_soup_getter), and holding
    the HTTP response open for the whole thing means Render's proxy (or the
    calling GitHub Actions curl) can kill the connection well before the job
    would have finished on its own -- the exact "refresh failed after 19
    minutes" symptom this was built to avoid. Returning immediately means the
    wake-up request always succeeds regardless of how long the job runs;
    check Render's own logs for the job's actual completion/failure, not the
    GitHub Actions run status."""
    _check_token(x_admin_token)
    logger.info("admin-triggered forecast refresh")
    background_tasks.add_task(_run_forecast_refresh_job)
    return {"status": "started"}


@router.post("/refresh/market-intel")
def trigger_market_intel_refresh(background_tasks: BackgroundTasks, x_admin_token: str | None = Header(default=None)):
    """Manual trigger for the hourly Kalshi + news/AI Race Intelligence job
    -- same rationale as /refresh/forecast above, including running as a
    background task so the response never waits on the full per-race loop."""
    _check_token(x_admin_token)
    logger.info("admin-triggered market/intel refresh")
    background_tasks.add_task(_run_market_intel_refresh_job)
    return {"status": "started"}
