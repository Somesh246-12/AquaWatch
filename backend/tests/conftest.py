"""AquaWatch Test Configuration and Fixtures."""

import sqlite3
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.main import app
from app.services.init_db import init_db


@pytest.fixture(scope="session")
def client():
    """Provides a reusable FastAPI TestClient across test sessions."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_db():
    """Provides an isolated in-memory SQLite database for unit tests with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Initialize tables and default zones
    init_db(engine_override=engine, session_factory_override=TestingSessionLocal)

    session = TestingSessionLocal()
    try:
        yield {
            "engine": engine,
            "session": session,
            "session_factory": TestingSessionLocal,
        }
    finally:
        session.close()
        engine.dispose()
