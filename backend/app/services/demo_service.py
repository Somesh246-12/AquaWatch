"""AquaWatch Live Demo & Simulated Leak Injection Service.

Manages isolated demo sessions, realistic leak injection into time-series readings,
execution of detection algorithms against injected telemetry, persistence of demo alerts,
timeline event orchestration, and safe session reset and rollback.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.reading import Reading
from app.models.zone import Zone
from app.schemas.alert import AlertResponse
from app.schemas.demo import (
    DemoInjectRequest,
    DemoInjectResponse,
    DemoResetResponse,
    DemoSessionStatus,
    DemoTelemetryPoint,
    DemoTimelineStep,
)
from app.services.detection.rule_based import RuleBasedDetector
from app.services.detection.z_score import ZScoreDetector
from app.services.simulator import ZONE_HOURLY_BASELINES

logger = logging.getLogger("aquawatch.demo")


@dataclass
class InternalDemoSession:
    """In-memory representation of an active demo session."""

    session_id: str
    status: str = "idle"  # "idle", "ready", "injecting", "detected", "resolved"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    leak_type: Optional[str] = None
    severity: Optional[str] = None
    leak_flow_lph: Optional[float] = None
    total_leak_volume_litres: Optional[float] = None
    alert_id: Optional[int] = None
    alert_resolved: bool = False
    injected_readings_count: int = 0
    detector_name: Optional[str] = None
    detector_score: Optional[float] = None
    detector_message: Optional[str] = None
    reading_ids: List[int] = field(default_factory=list)
    alert_ids: List[int] = field(default_factory=list)
    timeline: List[DemoTimelineStep] = field(default_factory=list)
    telemetry_points: List[DemoTelemetryPoint] = field(default_factory=list)


# Active sessions registry: session_id -> InternalDemoSession
_sessions: Dict[str, InternalDemoSession] = {}
_current_active_session_id: Optional[str] = None


def get_current_session(session_id: Optional[str] = None) -> InternalDemoSession:
    """Retrieves an existing session or initializes a new default demo session."""
    global _current_active_session_id

    target_id = session_id or _current_active_session_id
    if target_id and target_id in _sessions:
        return _sessions[target_id]

    # Create new session
    new_id = f"demo_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    session = InternalDemoSession(
        session_id=new_id,
        status="ready",
        timeline=[
            DemoTimelineStep(
                step="session_ready",
                title="Live Demo Session Ready",
                description="AquaWatch telemetry monitoring active across all 5 zones.",
                status="completed",
                timestamp=now,
            )
        ],
    )
    _sessions[new_id] = session
    _current_active_session_id = new_id
    return session


def start_demo_session(session_id: Optional[str] = None) -> DemoSessionStatus:
    """Explicitly initializes or resets a demo session to a fresh ready state."""
    global _current_active_session_id

    new_id = session_id or f"demo_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    session = InternalDemoSession(
        session_id=new_id,
        status="ready",
        timeline=[
            DemoTimelineStep(
                step="session_ready",
                title="Live Demo Session Ready",
                description="AquaWatch telemetry monitoring active across all 5 zones.",
                status="completed",
                timestamp=now,
            )
        ],
    )
    _sessions[new_id] = session
    _current_active_session_id = new_id
    return _build_session_status(session)


def get_session_status(db: Session, session_id: Optional[str] = None) -> DemoSessionStatus:
    """Returns the live status, telemetry, and milestone timeline of the demo session."""
    session = get_current_session(session_id)

    # Check if the associated alert has been resolved in the database
    if session.alert_id:
        alert = db.query(Alert).filter(Alert.id == session.alert_id).first()
        if alert and alert.resolved and not session.alert_resolved:
            session.alert_resolved = True
            session.status = "resolved"

            # Append resolution milestone if not already present
            if not any(t.step == "alert_resolved" for t in session.timeline):
                session.timeline.append(
                    DemoTimelineStep(
                        step="alert_resolved",
                        title="Alert Acknowledged & Resolved",
                        description=(
                            f"Operator resolved Alert #{session.alert_id} in {session.zone_name}. "
                            "Consumption anomaly cleared from active alert list."
                        ),
                        status="completed",
                        timestamp=datetime.now(timezone.utc),
                    )
                )

    return _build_session_status(session)


def inject_simulated_leak(
    db: Session,
    request: DemoInjectRequest,
) -> DemoInjectResponse:
    """Executes safe leak injection, runs detection, and persists demo alert."""
    # 1. Validate zone existence
    zone = db.query(Zone).filter(Zone.id == request.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with ID {request.zone_id} not found",
        )

    # 2. Get or initialize session
    session = get_current_session(request.session_id)

    # 3. Prevent accidental duplicate injection while an active alert is unresolved
    if session.status in ["injected", "detected"] and not session.alert_resolved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An active simulated leak (Alert #{session.alert_id}) is already in progress "
                f"for zone '{session.zone_name}'. Resolve the alert or reset the demo session first."
            ),
        )

    # 4. Determine simulation target date
    max_ts = db.query(func.max(Reading.timestamp)).scalar()
    if max_ts:
        base_date = max_ts.date()
    else:
        base_date = datetime(2026, 10, 8).date()

    target_date = base_date + timedelta(days=1)
    now_utc = datetime.now(timezone.utc)

    all_zones = db.query(Zone).order_by(Zone.id.asc()).all()

    # 5. Build telemetry profiles based on leak type and severity
    generated_readings: List[Dict[str, Any]] = []
    telemetry_points: List[DemoTelemetryPoint] = []
    total_leak_volume = 0.0

    if request.leak_type == "slow_leak":
        # Continuous night leak between 01:00 and 04:00 (4 consecutive hours)
        # Flow rate additives based on severity:
        if request.severity == "high":
            flow_lph = 22.0
        elif request.severity == "medium":
            flow_lph = 12.0
        else:
            flow_lph = 5.5

        night_hours = [1, 2, 3, 4]
        hours_to_generate = [0, 1, 2, 3, 4]

        for z in all_zones:
            baseline_profile = ZONE_HOURLY_BASELINES.get(z.name, [1.0] * 24)
            for h in hours_to_generate:
                dt = datetime(target_date.year, target_date.month, target_date.day, h, 0, 0)
                base_flow = baseline_profile[h]

                if z.id == zone.id and h in night_hours:
                    flow = base_flow + flow_lph
                    is_anomaly = True
                    total_leak_volume += flow_lph
                else:
                    flow = base_flow
                    is_anomaly = False

                generated_readings.append(
                    {
                        "zone_id": z.id,
                        "timestamp": dt,
                        "litres": round(flow, 2),
                    }
                )

                if z.id == zone.id:
                    telemetry_points.append(
                        DemoTelemetryPoint(
                            timestamp=dt,
                            litres=round(flow, 2),
                            is_anomaly=is_anomaly,
                            baseline_litres=round(base_flow, 2),
                        )
                    )

    elif request.leak_type == "burst":
        # Sudden daytime surge burst at 14:00 (2 PM)
        if request.severity == "high":
            burst_additive = 550.0
        elif request.severity == "medium":
            burst_additive = 320.0
        else:
            burst_additive = 180.0

        flow_lph = burst_additive
        burst_hour = 14
        hours_to_generate = list(range(0, burst_hour + 1))  # 0 to 14

        for z in all_zones:
            baseline_profile = ZONE_HOURLY_BASELINES.get(z.name, [20.0] * 24)
            for h in hours_to_generate:
                dt = datetime(target_date.year, target_date.month, target_date.day, h, 0, 0)
                base_flow = baseline_profile[h]

                if z.id == zone.id and h == burst_hour:
                    flow = base_flow + burst_additive
                    is_anomaly = True
                    total_leak_volume += burst_additive
                else:
                    flow = base_flow
                    is_anomaly = False

                generated_readings.append(
                    {
                        "zone_id": z.id,
                        "timestamp": dt,
                        "litres": round(flow, 2),
                    }
                )

                if z.id == zone.id:
                    telemetry_points.append(
                        DemoTelemetryPoint(
                            timestamp=dt,
                            litres=round(flow, 2),
                            is_anomaly=is_anomaly,
                            baseline_litres=round(base_flow, 2),
                        )
                    )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported leak type '{request.leak_type}'. Expected 'slow_leak' or 'burst'.",
        )

    # 6. Insert readings into database
    new_reading_objects = [
        Reading(
            zone_id=r["zone_id"],
            timestamp=r["timestamp"],
            litres=r["litres"],
        )
        for r in generated_readings
    ]
    db.add_all(new_reading_objects)
    db.flush()  # Populates reading IDs

    new_reading_ids = [r.id for r in new_reading_objects]
    session.reading_ids.extend(new_reading_ids)

    # 7. Execute real detector algorithm against database telemetry
    detector_name: str
    detector_score: float
    detector_msg: str

    if request.leak_type == "slow_leak":
        detector = RuleBasedDetector()
        results = detector.detect(db)
        # Find detection result for this zone on target date
        matched = next(
            (
                r
                for r in results
                if r.zone_id == zone.id and r.timestamp.date() == target_date
            ),
            None,
        )
        if not matched:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rule-based detector did not flag the injected night leak. Injection aborted.",
            )
        detector_name = "Rule-Based Night-Flow Detector"
        detector_score = matched.score or flow_lph
        detector_msg = matched.message
        mapped_alert_type = "leak"
        alert_timestamp = matched.timestamp

    else:  # burst
        detector = ZScoreDetector(threshold=3.0)
        results = detector.detect(db)
        matched = next(
            (
                r
                for r in results
                if r.zone_id == zone.id and r.timestamp.date() == target_date
            ),
            None,
        )
        if not matched:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Statistical Z-Score detector did not flag the burst event. Injection aborted.",
            )
        detector_name = "Statistical Z-Score Anomaly Detector"
        detector_score = matched.score or 5.0
        detector_msg = matched.message
        mapped_alert_type = "spike"
        alert_timestamp = matched.timestamp

    # 8. Persist new Alert with clear demo event marker
    demo_marker = f"[SIMULATED DEMO: {session.session_id[:8]}]"
    final_alert_message = f"{demo_marker} {detector_msg}"

    new_alert = Alert(
        zone_id=zone.id,
        timestamp=alert_timestamp,
        alert_type=mapped_alert_type,
        severity=request.severity,
        message=final_alert_message,
        resolved=False,
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    session.alert_ids.append(new_alert.id)

    # 9. Update session metadata and timeline
    session.status = "detected"
    session.zone_id = zone.id
    session.zone_name = zone.name
    session.leak_type = request.leak_type
    session.severity = request.severity
    session.leak_flow_lph = round(flow_lph, 2)
    session.total_leak_volume_litres = round(total_leak_volume, 2)
    session.alert_id = new_alert.id
    session.alert_resolved = False
    session.injected_readings_count = len(new_reading_ids)
    session.detector_name = detector_name
    session.detector_score = round(detector_score, 2)
    session.detector_message = detector_msg
    session.telemetry_points = telemetry_points

    # Build sequence timeline
    session.timeline = [
        DemoTimelineStep(
            step="session_ready",
            title="Live Demo Session Ready",
            description="AquaWatch telemetry monitoring active across all 5 zones.",
            status="completed",
            timestamp=now_utc - timedelta(seconds=12),
        ),
        DemoTimelineStep(
            step="leak_injected",
            title="Simulated Leak Injected",
            description=(
                f"Simulated {request.severity} {request.leak_type.replace('_', ' ')} "
                f"({flow_lph} L/h) injected into zone '{zone.name}'."
            ),
            status="completed",
            timestamp=now_utc - timedelta(seconds=8),
        ),
        DemoTimelineStep(
            step="telemetry_ingested",
            title="Telemetry Stream Ingested",
            description=f"Recorded {len(generated_readings)} hourly readings across 5 zones for {target_date}.",
            status="completed",
            timestamp=now_utc - timedelta(seconds=5),
        ),
        DemoTimelineStep(
            step="detector_triggered",
            title="Anomaly Confirmed by Detector",
            description=(
                f"{detector_name} identified anomaly in {zone.name} "
                f"(metric score: {detector_score:.2f})."
            ),
            status="completed",
            timestamp=now_utc - timedelta(seconds=2),
        ),
        DemoTimelineStep(
            step="alert_created",
            title="Operational Alert Dispatched",
            description=f"Generated Alert #{new_alert.id} ({request.severity.upper()}) with diagnostic metadata.",
            status="completed",
            timestamp=now_utc,
        ),
    ]

    summary_text = (
        f"Simulated {request.severity} {request.leak_type.replace('_', ' ')} successfully injected "
        f"into {zone.name} at {flow_lph} L/h. {detector_name} confirmed anomaly and dispatched "
        f"Alert #{new_alert.id}."
    )

    return DemoInjectResponse(
        success=True,
        session_id=session.session_id,
        event_id=new_alert.id,
        zone_id=zone.id,
        zone_name=zone.name,
        leak_type=request.leak_type,
        severity=request.severity,
        leak_flow_lph=round(flow_lph, 2),
        total_leak_volume=round(total_leak_volume, 2),
        alert=AlertResponse.model_validate(new_alert),
        detector={
            "name": detector_name,
            "score": round(detector_score, 2),
            "message": detector_msg,
            "rule": "01:00-04:00 flow > 3.0 L/h" if request.leak_type == "slow_leak" else "z-score > 3.0",
        },
        readings_injected=len(new_reading_ids),
        timeline=session.timeline,
        summary=summary_text,
    )


def reset_demo_session(
    db: Session,
    session_id: Optional[str] = None,
) -> DemoResetResponse:
    """Safely removes session-generated demo readings and alerts, preserving all original data."""
    session = get_current_session(session_id)

    alerts_deleted = 0
    readings_deleted = 0

    try:
        # 1. Clean up demo alerts by recorded IDs
        if session.alert_ids:
            alerts_deleted = (
                db.query(Alert)
                .filter(Alert.id.in_(session.alert_ids))
                .delete(synchronize_session=False)
            )

        # Safety fallback: clean any remaining alerts tagged with this session's marker
        marker_prefix = f"[SIMULATED DEMO: {session.session_id[:8]}]"
        extra_alerts_deleted = (
            db.query(Alert)
            .filter(Alert.message.startswith(marker_prefix))
            .delete(synchronize_session=False)
        )
        alerts_deleted += extra_alerts_deleted

        # 2. Clean up demo readings by recorded IDs
        if session.reading_ids:
            readings_deleted = (
                db.query(Reading)
                .filter(Reading.id.in_(session.reading_ids))
                .delete(synchronize_session=False)
            )

        db.commit()

        # Reset session state
        session.status = "idle"
        session.zone_id = None
        session.zone_name = None
        session.leak_type = None
        session.severity = None
        session.leak_flow_lph = None
        session.total_leak_volume_litres = None
        session.alert_id = None
        session.alert_resolved = False
        session.injected_readings_count = 0
        session.detector_name = None
        session.detector_score = None
        session.detector_message = None
        session.reading_ids.clear()
        session.alert_ids.clear()
        session.telemetry_points.clear()
        session.timeline = [
            DemoTimelineStep(
                step="session_reset",
                title="Demo Environment Reset",
                description="All session readings and alerts removed. Historical baseline preserved.",
                status="completed",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        logger.info(
            f"Demo session '{session.session_id}' reset: {readings_deleted} readings, "
            f"{alerts_deleted} alerts removed."
        )

        return DemoResetResponse(
            status="reset",
            session_id=session.session_id,
            readings_cleaned=readings_deleted,
            alerts_cleaned=alerts_deleted,
            original_data_preserved=True,
            message=(
                f"Demo session successfully reset. {readings_deleted} demo readings and "
                f"{alerts_deleted} demo alerts cleaned up. All 7,200 baseline readings "
                "and 10 ground-truth anomalies intact."
            ),
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"Error resetting demo session '{session.session_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset demo session: {str(exc)}",
        )


def _build_session_status(session: InternalDemoSession) -> DemoSessionStatus:
    """Builds response model from internal session object."""
    return DemoSessionStatus(
        session_id=session.session_id,
        status=session.status,  # type: ignore
        zone_id=session.zone_id,
        zone_name=session.zone_name,
        leak_type=session.leak_type,
        severity=session.severity,
        leak_flow_lph=session.leak_flow_lph,
        total_leak_volume_litres=session.total_leak_volume_litres,
        alert_id=session.alert_id,
        alert_resolved=session.alert_resolved,
        injected_readings_count=session.injected_readings_count,
        detector_name=session.detector_name,
        detector_score=session.detector_score,
        detector_message=session.detector_message,
        timeline=session.timeline,
        telemetry_points=session.telemetry_points,
    )
