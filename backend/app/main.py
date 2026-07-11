import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.config import settings
from app.ingestion.pipeline import ingest_polls
from app.ingestion.scheduler import start_scheduler, stop_scheduler
from app.routers import forecast, polls, simulations
from app.services.approval import seed_default_approval
from app.services.forecasting import generate_forecast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Looked up via the `database` module (not destructured at import time) so
    # tests can swap in a test engine/sessionmaker before startup runs.
    database.Base.metadata.create_all(bind=database.engine)

    db = database.SessionLocal()
    try:
        ingest_polls(db)
        seed_default_approval(db)
        # The forecast is generated here (once per app start) and again by the
        # scheduled refresh job every 24h — never on demand from the client,
        # so there's no user-facing "re-run" action.
        generate_forecast(db)
    finally:
        db.close()

    sched = start_scheduler()
    next_run = sched.get_jobs()[0].next_run_time
    logger.info("scheduled refresh job registered, next run at %s", next_run)
    yield
    stop_scheduler()


app = FastAPI(title="PA Governor Forecast API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(polls.router)
app.include_router(forecast.router)
app.include_router(simulations.router)


@app.get("/health")
def health():
    return {"status": "ok"}
