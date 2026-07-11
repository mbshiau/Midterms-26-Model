import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.config import settings
from app.ingestion.pipeline import ingest_polls
from app.ingestion.scheduler import start_scheduler, stop_scheduler
from app.routers import forecast, polls, races, simulations
from app.services.approval import seed_default_approval
from app.services.forecasting import generate_forecast, latest_forecast
from app.services.races import get_race_seed, seed_all_races

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Looked up via the `database` module (not destructured at import time) so
    # tests can swap in a test engine/sessionmaker before startup runs.
    database.Base.metadata.create_all(bind=database.engine)

    db = database.SessionLocal()
    try:
        seed_default_approval(db)
        races = seed_all_races(db)
        for race in races.values():
            race_seed = get_race_seed(race.state_code)
            ingest_polls(db, race, race_seed)
            # Only bootstrap a forecast the first time a race is seeded (no
            # snapshot yet). Every subsequent app restart must NOT re-run
            # this, or every existing race gets a spurious new snapshot each
            # time the container restarts for an unrelated reason (e.g.
            # adding a different state) -- forecast history is meant to
            # reflect real refresh events (the 24h scheduled job, or a
            # manual /simulate call), not process restarts.
            if latest_forecast(db, race) is None:
                generate_forecast(db, race)
    finally:
        db.close()

    sched = start_scheduler()
    next_run = sched.get_jobs()[0].next_run_time
    logger.info("scheduled refresh job registered, next run at %s", next_run)
    yield
    stop_scheduler()


app = FastAPI(title="Governor Race Forecast API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(races.router)
app.include_router(polls.router)
app.include_router(forecast.router)
app.include_router(simulations.router)


@app.get("/health")
def health():
    return {"status": "ok"}
