"""Health check response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for the /health response payload."""

    status: str = Field(default="ok", description="API health status", examples=["ok"])
    service: str = Field(default="AquaWatch API", description="Service identifier", examples=["AquaWatch API"])
    version: str = Field(default="0.1.0", description="Service version", examples=["0.1.0"])
    database: str = Field(default="connected", description="Database connectivity status", examples=["connected"])
