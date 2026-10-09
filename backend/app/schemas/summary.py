"""Pydantic schemas for Dashboard Summary endpoint."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TopZoneSummary(BaseModel):
    """Summary of the highest water-consuming zone."""

    id: int = Field(..., description="Zone identifier")
    name: str = Field(..., description="Zone name")
    litres: float = Field(..., description="Water consumption volume in litres")


class ZoneBudgetSummary(BaseModel):
    """Budget and consumption status for a single zone."""

    id: int = Field(..., description="Zone identifier")
    name: str = Field(..., description="Zone name")
    type: str = Field(..., description="Zone classification")
    daily_budget_litres: float = Field(..., description="Configured daily budget in litres")
    today_usage_litres: float = Field(..., description="Today's total usage in litres")
    budget_used_percent: float = Field(..., description="Percentage of daily budget consumed today")


class DashboardSummaryResponse(BaseModel):
    """Dashboard KPI summary response payload."""

    today_usage_litres: float = Field(..., description="Total water usage across all zones today")
    yesterday_usage_litres: float = Field(..., description="Total water usage across all zones yesterday")
    change_percent: float = Field(..., description="Percentage change in total usage versus yesterday")
    weekly_usage_litres: float = Field(..., description="Total water usage over the past 7 days")
    top_zone: Optional[TopZoneSummary] = Field(None, description="Highest consuming zone today")
    active_alerts: int = Field(..., description="Count of currently unresolved alerts")
    zones: List[ZoneBudgetSummary] = Field(..., description="Breakdown of usage and budget status per zone")
