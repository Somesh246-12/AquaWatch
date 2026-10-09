"""Tests for database connectivity and session lifecycle."""

from app.database import check_db_connection, get_db
from sqlalchemy.orm import Session


def test_database_connection():
    """Ensure database connection executes a basic query successfully."""
    assert check_db_connection() is True


def test_get_db_session_lifecycle():
    """Ensure get_db yields an active SQLAlchemy session and closes properly."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    # Finish the generator
    try:
        next(db_gen)
    except StopIteration:
        pass  # Expected lifecycle completion
