import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database


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
