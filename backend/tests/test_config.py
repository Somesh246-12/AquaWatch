"""Tests for configuration settings."""

from app.config import settings


def test_settings_loaded():
    """Verify default application settings are properly loaded."""
    assert settings.PROJECT_NAME == "AquaWatch API"
    assert "sqlite:///" in settings.DATABASE_URL
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0
