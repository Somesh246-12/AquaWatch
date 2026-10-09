"""Pydantic schemas for Alert entity."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AlertSeverity = Literal["low", "medium", "high"]
AlertType = Literal["leak", "spike", "abnormal_usage"]


class AlertBase(BaseModel):
    """Base schema for anomaly and leak alerts."""

    zone_id: int = Field(..., gt=0, description="Associated zone identifier", examples=[1])
    timestamp: datetime = Field(..., description="Timestamp of the alert occurrence")
    alert_type: AlertType = Field(
        ...,
        description="Type of anomaly (leak, spike, abnormal_usage)",
        examples=["leak"],
    )
    severity: AlertSeverity = Field(
        ...,
        description="Alert severity level (low, medium, high)",
        examples=["high"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Diagnostic alert message",
        examples=["Continuous night flow of 4.2 L/h detected between 01:00 and 04:00."],
    )
    resolved: bool = Field(default=False, description="Status of alert resolution")


class AlertCreate(AlertBase):
    """Schema for creating a new alert."""
    pass


class AlertResponse(AlertBase):
    """Schema for serializing an alert entity."""

    id: int = Field(..., description="Unique alert identifier", examples=[1])

    model_config = ConfigDict(from_attributes=True)
