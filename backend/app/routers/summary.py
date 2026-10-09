"""AquaWatch Dashboard Summary Router.

Provides aggregated KPIs, consumption trends, and zone budget tracking.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.summary import DashboardSummaryResponse
from app.services import summary_service

router = APIRouter(prefix="/summary", tags=["Summary"])


@router.get(
    "",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard summary",
    description="Returns aggregated metrics: today's usage, yesterday's usage, change %, weekly usage, top zone, active alerts, and zone budgets.",
)
def get_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    """Retrieve live dashboard summary metrics and zone statuses."""
    return summary_service.get_dashboard_summary(db=db)
