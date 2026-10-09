"""AquaWatch Live Demo Router.

Provides endpoints for interactive live demonstration:
- GET /demo/status: Retrieves active demo session state, metrics, and timeline
- POST /demo/start: Initializes or resets a demo session
- POST /demo/inject: Injects simulated leak telemetry, executes detection, and creates alerts
- POST /demo/reset: Ends session and safely removes session-generated data
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.demo import (
    DemoInjectRequest,
    DemoInjectResponse,
    DemoResetResponse,
    DemoSessionStatus,
)
from app.services.demo_service import (
    get_session_status,
    inject_simulated_leak,
    reset_demo_session,
    start_demo_session,
)

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get(
    "/status",
    response_model=DemoSessionStatus,
    status_code=status.HTTP_200_OK,
    summary="Get demo session status",
    description="Retrieves the current status, timeline, and telemetry points of the active demo session.",
)
def get_status(
    session_id: Optional[str] = Query(None, description="Optional session tracking ID"),
    db: Session = Depends(get_db),
) -> DemoSessionStatus:
    """Retrieve the current demo session state and milestone timeline."""
    return get_session_status(db=db, session_id=session_id)


@router.post(
    "/start",
    response_model=DemoSessionStatus,
    status_code=status.HTTP_200_OK,
    summary="Start new demo session",
    description="Initializes a new demo session or resets current state to ready.",
)
def start_session(
    session_id: Optional[str] = Query(None, description="Optional custom session ID"),
) -> DemoSessionStatus:
    """Initialize a new demo session."""
    return start_demo_session(session_id=session_id)


@router.post(
    "/inject",
    response_model=DemoInjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inject simulated leak",
    description="Simulates an anomalous water leak, runs the detection pipeline, and persists an alert.",
)
def inject_leak(
    payload: DemoInjectRequest,
    db: Session = Depends(get_db),
) -> DemoInjectResponse:
    """Inject simulated leak into selected zone, execute detection, and persist alert."""
    return inject_simulated_leak(db=db, request=payload)


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset demo session",
    description="Safely removes demo readings and alerts created during the session, preserving all baseline data.",
)
def reset_session(
    session_id: Optional[str] = Query(None, description="Optional session ID to clean up"),
    db: Session = Depends(get_db),
) -> DemoResetResponse:
    """End demo session and roll back session-created readings and alerts."""
    return reset_demo_session(db=db, session_id=session_id)
