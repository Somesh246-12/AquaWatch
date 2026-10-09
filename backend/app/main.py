"""AquaWatch - Main Application Entrypoint.

Initializes the FastAPI application, registers middleware, configures
lifespan database initialization, and includes routers.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, check_db_connection
from app.services.init_db import init_db
from app.routers import alerts, conservation, demo, detection, health, readings, summary, zones

# Configure basic logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("aquawatch")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown events."""
    logger.info("Initializing AquaWatch backend...")
    
    # Initialize database tables, default monitoring zones, and baseline telemetry if empty
    try:
        zones = init_db(auto_seed_data=True)
        logger.info(f"Database initialized with {len(zones)} monitoring zones.")
    except Exception as exc:
        logger.error(f"Error during database initialization: {exc}")

    yield

    logger.info("Shutting down AquaWatch backend.")


# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
cors_origins_list = (
    settings.CORS_ORIGINS
    if isinstance(settings.CORS_ORIGINS, list)
    else [settings.CORS_ORIGINS]
)

cors_kwargs = {
    "allow_origins": cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.CORS_ORIGIN_REGEX:
    cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Register routers
app.include_router(health.router)
app.include_router(zones.router)
app.include_router(readings.router)
app.include_router(alerts.router)
app.include_router(summary.router)
app.include_router(detection.router)
app.include_router(conservation.router)
app.include_router(demo.router)


@app.get("/", tags=["Root"])
def read_root():
    """Welcome endpoint providing quick links to documentation and status."""
    return {
        "message": "Welcome to AquaWatch API - Water Conservation through Digital Monitoring",
        "docs": "/docs",
        "health": "/health",
        "version": settings.VERSION,
    }
