"""Pydantic schemas for Conservation Intelligence API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

BudgetStatus = Literal["normal", "warning", "exceeded"]
RecommendationPriority = Literal["low", "medium", "high", "critical"]


# ==============================================================================
# 1. WATER BUDGET SCHEMAS
# ==============================================================================

class ZoneBudgetStatus(BaseModel):
    """Detailed daily water budget performance for an individual zone."""

    zone_id: int = Field(..., description="Unique zone identifier", examples=[1])
    zone_name: str = Field(..., description="Name of the zone", examples=["Household"])
    zone_type: str = Field(..., description="Classification of the zone", examples=["residential"])
    daily_budget_litres: float = Field(..., gt=0, description="Configured daily budget in litres", examples=[1500.0])
    actual_consumption_litres: float = Field(..., ge=0, description="Actual consumption recorded on date", examples=[1350.0])
    remaining_budget_litres: float = Field(..., description="Remaining budget allowance (can be negative if exceeded)", examples=[150.0])
    consumed_percent: float = Field(..., ge=0, description="Percentage of daily budget consumed", examples=[90.0])
    is_exceeded: bool = Field(..., description="Whether consumption has exceeded the daily allowance", examples=[False])
    status: BudgetStatus = Field(..., description="Budget status: normal (<80%), warning (80%-<100%), exceeded (>=100%)", examples=["warning"])


class ConservationBudgetsResponse(BaseModel):
    """Overall water-budget consumption status across all zones."""

    date: str = Field(..., description="Reference date for calculations (YYYY-MM-DD)", examples=["2026-09-20"])
    total_budget_litres: float = Field(..., description="Aggregate daily budget across all zones", examples=[19000.0])
    total_actual_litres: float = Field(..., description="Aggregate consumption recorded on date", examples=[16500.0])
    total_remaining_litres: float = Field(..., description="Aggregate remaining allowance", examples=[2500.0])
    overall_consumed_percent: float = Field(..., description="Aggregate percentage of total budget consumed", examples=[86.84])
    overall_status: BudgetStatus = Field(..., description="System-wide budget status", examples=["warning"])
    zones: List[ZoneBudgetStatus] = Field(..., description="Per-zone budget performance breakdown")


# ==============================================================================
# 2. CONSERVATION RECOMMENDATIONS (TIPS) SCHEMAS
# ==============================================================================

class ConservationRecommendation(BaseModel):
    """Actionable water-conservation guidance derived from real data."""

    id: str = Field(..., description="Stable recommendation identifier", examples=["leak-repair-zone-1-alert-12"])
    category: str = Field(..., description="Recommendation category (leak_repair, budget_exceeded, budget_warning, high_consumption, general_tip)", examples=["leak_repair"])
    title: str = Field(..., description="Succinct title", examples=["Urgent: Inspect Leak in Household"])
    description: str = Field(..., description="Human-readable explanation and suggested action", examples=["Active continuous night flow detected. Inspect fixtures immediately."])
    priority: RecommendationPriority = Field(..., description="Action priority (low, medium, high, critical)", examples=["critical"])
    zone_id: Optional[int] = Field(None, description="Relevant zone identifier if zone-specific", examples=[1])
    zone_name: Optional[str] = Field(None, description="Relevant zone name if zone-specific", examples=["Household"])
    supporting_data: Optional[Dict[str, Any]] = Field(None, description="Diagnostic values and metrics supporting recommendation")


class ConservationTipsResponse(BaseModel):
    """Collection of targeted conservation recommendations."""

    date: str = Field(..., description="Reference date of observations", examples=["2026-09-20"])
    total_recommendations: int = Field(..., description="Total count of active recommendations generated", examples=[3])
    recommendations: List[ConservationRecommendation] = Field(..., description="Ranked list of conservation recommendations")


# ==============================================================================
# 3. SAVINGS ESTIMATOR SCHEMAS
# ==============================================================================

class LeakSavingsEstimate(BaseModel):
    """Monetary and volumetric water loss projection for a single leak."""

    alert_id: Optional[int] = Field(None, description="Associated alert ID", examples=[1])
    zone_id: int = Field(..., description="Zone identifier where leak occurred", examples=[1])
    zone_name: Optional[str] = Field(None, description="Zone name", examples=["Household"])
    timestamp: Optional[datetime] = Field(None, description="Leak detection timestamp")
    leak_flow_lph: Optional[float] = Field(None, description="Estimated leak flow rate in Litres/hour", examples=[4.8])
    assumed_hours_per_day: float = Field(..., description="Assumed leak persistence hours per day", examples=[24.0])
    daily_wasted_litres: Optional[float] = Field(None, description="Projected daily water loss in litres", examples=[115.2])
    monthly_wasted_litres: Optional[float] = Field(None, description="Projected 30-day water loss in litres", examples=[3456.0])
    monthly_savings: Optional[float] = Field(None, description="Projected monthly monetary savings if repaired", examples=[8.64])
    status: str = Field(..., description="Estimation status: 'estimated' or 'unavailable'", examples=["estimated"])
    message: str = Field(..., description="Diagnostic details or explanation of estimate", examples=["Flow rate estimated from night-flow leak detector."])
    is_estimate: bool = Field(default=True, description="Explicit disclaimer that this is a projection")


class ConservationSavingsResponse(BaseModel):
    """Aggregate financial and volumetric savings projections across detected leaks."""

    tariff_per_kl: float = Field(..., description="Configured water tariff in currency per 1,000 litres", examples=[2.5])
    currency: str = Field(default="USD", description="Currency symbol or abbreviation", examples=["USD"])
    assumed_hours_per_day: float = Field(..., description="Assumed daily leak hours used in calculations", examples=[24.0])
    total_leaks_evaluated: int = Field(..., description="Total leak alerts inspected", examples=[4])
    actionable_leaks_count: int = Field(..., description="Count of leaks with credible flow estimates", examples=[4])
    total_daily_wasted_litres: float = Field(..., description="Total projected daily water waste in litres", examples=[460.8])
    total_monthly_wasted_litres: float = Field(..., description="Total projected 30-day water waste in litres", examples=[13824.0])
    total_monthly_savings: float = Field(..., description="Total projected monthly cost savings if repaired", examples=[34.56])
    leak_estimates: List[LeakSavingsEstimate] = Field(..., description="Breakdown per detected leak event")
    disclaimer: str = Field(
        default="Estimated savings are projections based on assumed daily leak duration and configured tariffs. They are not guaranteed or measured savings.",
        description="Legal and analytical disclaimer",
    )
