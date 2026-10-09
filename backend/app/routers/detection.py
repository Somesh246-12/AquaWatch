"""AquaWatch Anomaly Detection Router.

Exposes pipeline execution endpoint to run multi-detector anomaly evaluation
and persist detected anomalies as alerts.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.detection import DetectionRunResponse
from app.services.detection.evaluator import run_detection_and_persist_alerts

router = APIRouter(prefix="/detection", tags=["Detection"])


@router.post(
    "/run",
    response_model=DetectionRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute detection pipeline",
    description="Runs all three detectors (Rule-based, Z-score, Isolation Forest), persists unique alerts, and returns evaluation benchmarks.",
)
def run_detection(
    contamination: float = Query(0.02, ge=0.001, le=0.5, description="Expected contamination rate for Isolation Forest"),
    db: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Execute anomaly detection pipeline, persist non-duplicate alerts, and return evaluation."""
    results = run_detection_and_persist_alerts(session=db, contamination=contamination)
    return DetectionRunResponse(**results)
