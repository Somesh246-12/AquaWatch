"""AquaWatch Alerts Router.

Exposes endpoints for querying, inspecting, and resolving anomaly alerts.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alert import AlertResponse
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])

VALID_SEVERITIES = {"low", "medium", "high"}
VALID_ALERT_TYPES = {"leak", "spike", "abnormal_usage"}


@router.get(
    "",
    response_model=List[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="List alerts",
    description="Retrieve anomaly alerts with optional filtering, ordered newest first.",
)
def get_alerts(
    zone_id: Optional[int] = Query(None, description="Filter by zone ID"),
    severity: Optional[str] = Query(None, description="Filter by severity ('low', 'medium', 'high')"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type ('leak', 'spike', 'abnormal_usage')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
) -> List[AlertResponse]:
    """Retrieve filtered alerts ordered by timestamp descending."""
    if severity is not None and severity.lower() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity '{severity}'. Allowed values: {sorted(list(VALID_SEVERITIES))}",
        )

    if alert_type is not None and alert_type.lower() not in VALID_ALERT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid alert_type '{alert_type}'. Allowed values: {sorted(list(VALID_ALERT_TYPES))}",
        )

    if zone_id is not None and zone_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zone_id must be a positive integer.",
        )

    return alert_service.get_alerts(
        db=db,
        zone_id=zone_id,
        severity=severity.lower() if severity else None,
        resolved=resolved,
        alert_type=alert_type.lower() if alert_type else None,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single alert",
    description="Retrieve an alert by identifier. Returns 404 if not found.",
)
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertResponse:
    """Retrieve a single alert by its identifier."""
    alert = alert_service.get_alert_by_id(db, alert_id=alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found.",
        )
    return alert


@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve alert",
    description="Marks an alert as resolved. Returns the updated alert.",
)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertResponse:
    """Mark an existing alert as resolved."""
    alert = alert_service.resolve_alert(db, alert_id=alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found.",
        )
    return alert
