"""AquaWatch Health Check Router."""

from fastapi import APIRouter, status
from app.config import settings
from app.database import check_db_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns the operational status of the AquaWatch API and database connectivity.",
)
def get_health() -> HealthResponse:
    """Verify backend health and database connectivity."""
    db_healthy = check_db_connection()
    return HealthResponse(
        status="ok" if db_healthy else "degraded",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        database="connected" if db_healthy else "disconnected",
    )
