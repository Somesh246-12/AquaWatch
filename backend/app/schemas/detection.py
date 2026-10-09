"""Pydantic schemas for Detection API endpoints."""

from typing import Any, Dict
from pydantic import BaseModel, Field


class DetectionRunResponse(BaseModel):
    """Response payload for POST /detection/run."""

    status: str = Field(default="completed", description="Execution status")
    candidate_detections: int = Field(default=0, description="Total raw candidate events identified by all detectors")
    alerts_created: int = Field(..., description="Number of new unique alerts inserted into database")
    alerts_existing: int = Field(..., description="Number of candidate events skipped as duplicates or already present")
    detectors: Dict[str, Any] = Field(..., description="Summary of detector findings")
    evaluation: Dict[str, Any] = Field(..., description="Benchmark evaluation metrics vs ground truth")
