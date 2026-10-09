"""Pydantic schemas for Reading entity."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReadingBase(BaseModel):
    """Base schema for water consumption readings."""

    zone_id: int = Field(..., gt=0, description="Associated zone identifier", examples=[1])
    timestamp: datetime = Field(..., description="Timestamp of recorded reading")
    litres: float = Field(..., ge=0, description="Volume consumed in litres (>= 0)", examples=[45.5])

    @field_validator("litres")
    @classmethod
    def validate_non_negative_litres(cls, value: float) -> float:
        """Validate that consumed water volume cannot be negative."""
        if value < 0:
            raise ValueError("Water reading litres cannot be negative")
        return value


class ReadingCreate(ReadingBase):
    """Schema for recording a new water consumption reading."""
    pass


class ReadingResponse(ReadingBase):
    """Schema for serializing a water consumption reading."""

    id: int = Field(..., description="Unique reading identifier", examples=[101])

    model_config = ConfigDict(from_attributes=True)


class DailyReadingResponse(BaseModel):
    """Schema for daily aggregated water consumption."""

    date: str = Field(..., description="Date formatted as YYYY-MM-DD", examples=["2026-09-20"])
    zone_id: int = Field(..., description="Associated zone identifier", examples=[1])
    zone_name: Optional[str] = Field(None, description="Name of the zone", examples=["Household"])
    litres: float = Field(..., description="Total water consumption volume for the day in litres", examples=[1234.5])
