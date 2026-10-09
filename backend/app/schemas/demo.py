"""Pydantic schemas for the AquaWatch Live Demo mode."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.alert import AlertResponse


class DemoInjectRequest(BaseModel):
    """Payload to inject a simulated leak or burst event."""

    zone_id: int = Field(..., ge=1, description="Target zone identifier")
    leak_type: Literal["slow_leak", "burst"] = Field(
        default="slow_leak",
        description="Type of leak profile: slow_leak (night flow) or burst (high-volume spike)",
    )
    severity: Literal["low", "medium", "high"] = Field(
        default="high",
        description="Severity level scaling the anomalous flow volume",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session tracking identifier",
    )


class DemoTimelineStep(BaseModel):
    """A milestone step in the demo execution lifecycle."""

    step: str = Field(..., description="Unique step identifier")
    title: str = Field(..., description="Human-readable step title")
    description: str = Field(..., description="Diagnostic description of the milestone")
    status: Literal["completed", "active", "pending"] = Field(..., description="Status of the step")
    timestamp: datetime = Field(..., description="Timestamp when milestone occurred")


class DemoTelemetryPoint(BaseModel):
    """Hourly consumption point generated for the demo view."""

    timestamp: datetime
    litres: float
    is_anomaly: bool
    baseline_litres: float


class DemoSessionStatus(BaseModel):
    """Current status and progress of the active demo session."""

    session_id: str
    status: Literal["idle", "ready", "injecting", "detected", "resolved"]
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
    timeline: List[DemoTimelineStep] = Field(default_factory=list)
    telemetry_points: List[DemoTelemetryPoint] = Field(default_factory=list)


class DemoInjectResponse(BaseModel):
    """Result of a simulated leak injection and detector evaluation."""

    success: bool
    session_id: str
    event_id: int
    zone_id: int
    zone_name: str
    leak_type: str
    severity: str
    leak_flow_lph: float
    total_leak_volume: float
    alert: AlertResponse
    detector: Dict[str, Any]
    readings_injected: int
    timeline: List[DemoTimelineStep]
    summary: str


class DemoResetResponse(BaseModel):
    """Result of ending a demo session and cleaning up session data."""

    status: str
    session_id: Optional[str] = None
    readings_cleaned: int
    alerts_cleaned: int
    original_data_preserved: bool
    message: str
