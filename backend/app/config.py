"""AquaWatch Configuration Module.

Manages application settings, database paths, and environment configurations
using Pydantic Settings.
"""

from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory paths
# BACKEND_DIR: .../AquaWatch/backend
# WORKSPACE_DIR: .../AquaWatch
BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BACKEND_DIR.parent
DATA_DIR = WORKSPACE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application configuration settings."""

    PROJECT_NAME: str = "AquaWatch API"
    PROJECT_DESCRIPTION: str = "Water Conservation through Digital Monitoring"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database configuration (SQLite default)
    DATABASE_URL: str = f"sqlite:///{DATA_DIR.as_posix()}/aquawatch.db"

    # CORS configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    # Allow all *.vercel.app deployment preview and production URLs by default
    CORS_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"

    # Water conservation settings
    DEFAULT_WATER_TARIFF_PER_KL: float = 2.50  # Currency per 1,000 litres (e.g. $2.50 / kL)
    DEFAULT_LEAK_HOURS_PER_DAY: float = 24.0   # Assumed leak persistence hours/day

    # Default monitored zones with daily water budgets (in litres/day)
    DEFAULT_ZONES: List[dict] = [
        {"name": "Household", "type": "residential", "daily_budget_litres": 1500.0},
        {"name": "Hostel Block", "type": "residential_bulk", "daily_budget_litres": 5000.0},
        {"name": "Garden", "type": "irrigation", "daily_budget_litres": 2500.0},
        {"name": "Kitchen", "type": "commercial_facility", "daily_budget_litres": 2000.0},
        {"name": "Community Tank", "type": "storage_distribution", "daily_budget_litres": 8000.0},
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """Convert comma-separated origin strings into a list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings singleton
settings = Settings()
