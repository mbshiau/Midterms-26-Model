import logging

from fastapi import APIRouter, Header, HTTPException

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
def trigger_forecast_refresh(x_admin_token: str | None = Header(default=None)):
    """Manual trigger for the noon/7pm forecast-refresh job (approval +
    generic ballot + poll scrape + Monte Carlo regen, every race).

    Exists because Render's free tier spins the service down between
    requests -- the in-process APScheduler job (app.ingestion.scheduler)
    silently misses its wall-clock slot if nothing hit the service around
    12:05/19:05 ET. An external cron (see .github/workflows) hits this
    endpoint on the same schedule instead; the request itself wakes the
    service, so there's no window for the job to be skipped."""
    _check_token(x_admin_token)
    logger.info("admin-triggered forecast refresh")
    _run_forecast_refresh_job()
    return {"status": "ok"}


@router.post("/refresh/market-intel")
def trigger_market_intel_refresh(x_admin_token: str | None = Header(default=None)):
    """Manual trigger for the hourly Kalshi + news/AI Race Intelligence job
    -- same rationale as /refresh/forecast above."""
    _check_token(x_admin_token)
    logger.info("admin-triggered market/intel refresh")
    _run_market_intel_refresh_job()
    return {"status": "ok"}
