"""Pydantic schemas for Ground Truth Injected Anomaly entity.

GROUND TRUTH NOTICE:
This schema represents the ground truth injected anomalies from the simulator.
These records are reserved strictly for evaluating detector accuracy (Precision,
Recall, and F1-score) and must not be used during detection inference.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AnomalyType = Literal["slow_leak", "burst", "wastage_day"]


class InjectedAnomalyBase(BaseModel):
    """Base schema for ground truth injected anomalies."""

    zone_id: int = Field(..., gt=0, description="Associated zone identifier", examples=[1])
    timestamp: datetime = Field(..., description="Timestamp when the anomaly was injected")
    anomaly_type: AnomalyType = Field(
        ...,
        description="Type of injected anomaly (slow_leak, burst, wastage_day)",
        examples=["slow_leak"],
    )


class InjectedAnomalyCreate(InjectedAnomalyBase):
    """Schema for recording a ground truth injected anomaly."""
    pass


class InjectedAnomalyResponse(InjectedAnomalyBase):
    """Schema for serializing a ground truth injected anomaly."""

    id: int = Field(..., description="Unique anomaly identifier", examples=[1])

    model_config = ConfigDict(from_attributes=True)
