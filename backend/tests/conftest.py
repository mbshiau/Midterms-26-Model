import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.config import settings


@pytest.fixture(autouse=True)
def _no_ai_rate_limit_pause(monkeypatch):
    # app.services.ai_summary paces real AI-provider calls to avoid rate
    # limiting -- without this, any test that exercises that pacing would
    # spend real wall-clock seconds sleeping.
    monkeypatch.setattr(settings, "ai_min_seconds_between_calls", 0.0)


@pytest.fixture(autouse=True)
def _fast_bootstrap_forecasts(monkeypatch):
    # app.main's lifespan bootstraps one forecast per seeded race on every
    # `client` fixture use -- with the full HOUSE_RACES registry now seeded
    # (435 districts, on top of Governor/Senate), that's ~470 races' worth
    # of Monte Carlo simulation on every single test that touches `client`.
    # Every test that cares about simulation precision already passes its
    # own explicit n_simulations (see test_simulation.py, test_api.py's
    # /simulate calls) rather than relying on this default, so lowering it
    # only speeds up the throwaway startup bootstrap, not anything a test
    # actually asserts against.
    monkeypatch.setattr(settings, "default_n_simulations", 200)


@pytest.fixture()
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


@pytest.fixture()
def client(test_engine):
    from app.main import app  # imported after engine patch so lifespan sees it

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(test_engine):
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()
