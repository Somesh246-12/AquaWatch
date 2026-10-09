"""Pydantic schemas for Zone entity."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ZoneBase(BaseModel):
    """Base schema for Zone attributes."""

    name: str = Field(..., min_length=1, max_length=100, description="Zone name", examples=["Household"])
    type: str = Field(..., min_length=1, max_length=50, description="Zone classification", examples=["residential"])
    daily_budget_litres: float = Field(..., gt=0, description="Daily water budget in litres (> 0)", examples=[1500.0])

    @field_validator("daily_budget_litres")
    @classmethod
    def validate_budget_positive(cls, value: float) -> float:
        """Validate that the daily water budget is strictly positive."""
        if value <= 0:
            raise ValueError("daily_budget_litres must be strictly greater than 0")
        return value


class ZoneCreate(ZoneBase):
    """Schema for creating a new zone."""
    pass


class ZoneResponse(ZoneBase):
    """Schema for serializing a zone entity."""

    id: int = Field(..., description="Unique zone identifier", examples=[1])

    model_config = ConfigDict(from_attributes=True)
