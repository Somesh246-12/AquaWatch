"""AquaWatch Conservation Service Layer.

Implements water-budget tracking, data-driven conservation recommendations,
and monetary/volumetric savings estimations for detected leaks.
"""

from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert
from app.models.reading import Reading
from app.models.zone import Zone
from app.schemas.conservation import (
    BudgetStatus,
    ConservationBudgetsResponse,
    ConservationRecommendation,
    ConservationSavingsResponse,
    ConservationTipsResponse,
    LeakSavingsEstimate,
    ZoneBudgetStatus,
)


def _resolve_reference_date(db: Session, target_date: Optional[Union[date, str]] = None) -> date:
    """Resolves target date or falls back to latest available reading date in DB."""
    if target_date is not None:
        if isinstance(target_date, str):
            try:
                return datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Invalid date format '{target_date}'. Expected YYYY-MM-DD.")
        elif isinstance(target_date, datetime):
            return target_date.date()
        elif isinstance(target_date, date):
            return target_date

    max_timestamp = db.query(func.max(Reading.timestamp)).scalar()
    if max_timestamp:
        return max_timestamp.date()
    return datetime.now().date()


# ==============================================================================
# 1. WATER BUDGET SERVICE
# ==============================================================================

def calculate_zone_budgets(
    db: Session,
    target_date: Optional[Union[date, str]] = None,
) -> ConservationBudgetsResponse:
    """Calculates daily consumption, remaining allowances, and budget status per zone.

    Status Threshold Rules:
    - Below 80%: 'normal'
    - From 80% to below 100%: 'warning'
    - At or above 100%: 'exceeded'
    """
    ref_date = _resolve_reference_date(db, target_date)
    ref_date_str = str(ref_date)

    zones = db.query(Zone).order_by(Zone.id.asc()).all()

    # Query sum of readings per zone for the given calendar date
    date_col = func.date(Reading.timestamp)
    usage_query = (
        db.query(Reading.zone_id, func.sum(Reading.litres))
        .filter(date_col == ref_date_str)
        .group_by(Reading.zone_id)
        .all()
    )
    usage_map = {row[0]: float(row[1]) for row in usage_query}

    zone_statuses: List[ZoneBudgetStatus] = []
    total_budget = 0.0
    total_actual = 0.0

    for z in zones:
        actual = round(usage_map.get(z.id, 0.0), 2)
        budget = round(float(z.daily_budget_litres), 2)
        remaining = round(budget - actual, 2)

        total_budget += budget
        total_actual += actual

        if budget > 0:
            consumed_pct = round((actual / budget) * 100.0, 2)
        else:
            consumed_pct = 0.0

        is_exceeded = actual >= budget

        if consumed_pct < 80.0:
            status: BudgetStatus = "normal"
        elif consumed_pct < 100.0:
            status = "warning"
        else:
            status = "exceeded"

        zone_statuses.append(
            ZoneBudgetStatus(
                zone_id=z.id,
                zone_name=z.name,
                zone_type=z.type,
                daily_budget_litres=budget,
                actual_consumption_litres=actual,
                remaining_budget_litres=remaining,
                consumed_percent=consumed_pct,
                is_exceeded=is_exceeded,
                status=status,
            )
        )

    total_budget = round(total_budget, 2)
    total_actual = round(total_actual, 2)
    total_remaining = round(total_budget - total_actual, 2)

    if total_budget > 0:
        overall_pct = round((total_actual / total_budget) * 100.0, 2)
    else:
        overall_pct = 0.0

    if overall_pct < 80.0:
        overall_status: BudgetStatus = "normal"
    elif overall_pct < 100.0:
        overall_status = "warning"
    else:
        overall_status = "exceeded"

    return ConservationBudgetsResponse(
        date=ref_date_str,
        total_budget_litres=total_budget,
        total_actual_litres=total_actual,
        total_remaining_litres=total_remaining,
        overall_consumed_percent=overall_pct,
        overall_status=overall_status,
        zones=zone_statuses,
    )


# ==============================================================================
# 2. CONSERVATION RECOMMENDATIONS SERVICE
# ==============================================================================

def generate_conservation_recommendations(
    db: Session,
    target_date: Optional[Union[date, str]] = None,
) -> ConservationTipsResponse:
    """Generates targeted, non-duplicated conservation recommendations from database observations.

    Prioritizes:
    1. Unresolved leak alerts (highest urgency inspection & repair)
    2. Zones exceeding daily budget (critical consumption curtailment)
    3. Zones approaching daily budget warning threshold (precautionary saving tips)
    4. Highest consuming zone observation (efficiency recommendations)
    5. General water conservation best practices when operating under optimal conditions
    """
    ref_date = _resolve_reference_date(db, target_date)
    ref_date_str = str(ref_date)

    budgets_response = calculate_zone_budgets(db, target_date=ref_date)
    zones_map = {z.zone_id: z for z in budgets_response.zones}

    recommendations: List[ConservationRecommendation] = []
    seen_ids = set()

    # 1. Unresolved leak alerts
    active_leaks = (
        db.query(Alert, Zone)
        .join(Zone, Alert.zone_id == Zone.id)
        .filter(Alert.resolved == False, Alert.alert_type == "leak")
        .order_by(Alert.timestamp.desc())
        .all()
    )

    leak_zones_processed = set()
    for alert, zone in active_leaks:
        if alert.zone_id in leak_zones_processed:
            continue
        leak_zones_processed.add(alert.zone_id)

        rec_id = f"leak-repair-zone-{alert.zone_id}"
        if rec_id not in seen_ids:
            seen_ids.add(rec_id)
            priority = "critical" if alert.severity == "high" else "high"
            recommendations.append(
                ConservationRecommendation(
                    id=rec_id,
                    category="leak_repair",
                    title=f"Inspect and Repair Active Leak in {zone.name}",
                    description=(
                        f"Active unresolved leak detected in {zone.name} (Alert #{alert.id}). "
                        f"Investigate shut-off valves, pipe fittings, and fixtures immediately to halt water loss."
                    ),
                    priority=priority,
                    zone_id=zone.id,
                    zone_name=zone.name,
                    supporting_data={
                        "alert_id": alert.id,
                        "alert_timestamp": alert.timestamp.isoformat(),
                        "severity": alert.severity,
                        "alert_message": alert.message,
                    },
                )
            )

    # 2. Budget exceeded zones (consumed_percent >= 100%)
    for zb in budgets_response.zones:
        if zb.status == "exceeded":
            rec_id = f"budget-exceeded-zone-{zb.zone_id}"
            if rec_id not in seen_ids:
                seen_ids.add(rec_id)
                excess = round(zb.actual_consumption_litres - zb.daily_budget_litres, 2)
                recommendations.append(
                    ConservationRecommendation(
                        id=rec_id,
                        category="budget_exceeded",
                        title=f"Budget Exceeded in {zb.zone_name}",
                        description=(
                            f"{zb.zone_name} has used {zb.consumed_percent:.1f}% of its daily budget "
                            f"({zb.actual_consumption_litres:.1f} L vs {zb.daily_budget_litres:.1f} L allowance), "
                            f"exceeding limits by {excess:.1f} L. Implement immediate consumption curtailment."
                        ),
                        priority="high",
                        zone_id=zb.zone_id,
                        zone_name=zb.zone_name,
                        supporting_data={
                            "daily_budget_litres": zb.daily_budget_litres,
                            "actual_consumption_litres": zb.actual_consumption_litres,
                            "excess_litres": excess,
                            "consumed_percent": zb.consumed_percent,
                        },
                    )
                )

    # 3. Budget warning zones (80% <= consumed_percent < 100%)
    for zb in budgets_response.zones:
        if zb.status == "warning":
            rec_id = f"budget-warning-zone-{zb.zone_id}"
            if rec_id not in seen_ids:
                seen_ids.add(rec_id)
                recommendations.append(
                    ConservationRecommendation(
                        id=rec_id,
                        category="budget_warning",
                        title=f"Water Conservation Notice for {zb.zone_name}",
                        description=(
                            f"{zb.zone_name} has reached {zb.consumed_percent:.1f}% of its daily allowance "
                            f"({zb.actual_consumption_litres:.1f} / {zb.daily_budget_litres:.1f} L). "
                            f"Restrict non-essential usage to prevent exceeding budget."
                        ),
                        priority="medium",
                        zone_id=zb.zone_id,
                        zone_name=zb.zone_name,
                        supporting_data={
                            "daily_budget_litres": zb.daily_budget_litres,
                            "actual_consumption_litres": zb.actual_consumption_litres,
                            "consumed_percent": zb.consumed_percent,
                            "remaining_budget_litres": zb.remaining_budget_litres,
                        },
                    )
                )

    # 4. Highest-consuming zone observation
    active_zones_with_usage = [zb for zb in budgets_response.zones if zb.actual_consumption_litres > 0.0]
    if active_zones_with_usage:
        top_zone = max(active_zones_with_usage, key=lambda z: z.actual_consumption_litres)
        rec_id = f"high-consumption-zone-{top_zone.zone_id}"
        # Ensure we do not spam duplicate if already reported under exceeded
        if rec_id not in seen_ids and top_zone.status != "exceeded":
            seen_ids.add(rec_id)
            recommendations.append(
                ConservationRecommendation(
                    id=rec_id,
                    category="high_consumption",
                    title=f"Primary Consumer: {top_zone.zone_name}",
                    description=(
                        f"{top_zone.zone_name} is today's primary water consumer with "
                        f"{top_zone.actual_consumption_litres:.1f} L recorded. Consider scheduling irrigation "
                        f"or installing low-flow flow regulators to optimize efficiency."
                    ),
                    priority="low",
                    zone_id=top_zone.zone_id,
                    zone_name=top_zone.zone_name,
                    supporting_data={
                        "actual_consumption_litres": top_zone.actual_consumption_litres,
                        "consumed_percent": top_zone.consumed_percent,
                    },
                )
            )

    # 5. General conservation tip if no critical issues present
    if not recommendations:
        rec_id = "general-conservation-tip"
        recommendations.append(
            ConservationRecommendation(
                id=rec_id,
                category="general_tip",
                title="Optimal System Conservation Maintained",
                description=(
                    "All zones are operating well within daily budget thresholds with zero active anomaly alerts. "
                    "Routine preventative audits and automated sensor monitoring sustain sustainable community water savings."
                ),
                priority="low",
                zone_id=None,
                zone_name=None,
                supporting_data={"system_status": "optimal"},
            )
        )

    return ConservationTipsResponse(
        date=ref_date_str,
        total_recommendations=len(recommendations),
        recommendations=recommendations,
    )


# ==============================================================================
# 3. SAVINGS ESTIMATOR SERVICE
# ==============================================================================

def calculate_leak_savings(
    db: Session,
    tariff_per_kl: Optional[float] = None,
    hours_per_day: Optional[float] = None,
    zone_id: Optional[int] = None,
) -> ConservationSavingsResponse:
    """Calculates volumetric and monetary water loss projections for detected leaks.

    Formulas:
    - Daily wasted litres = leak flow (L/h) * assumed leak hours per day
    - Monthly wasted litres = daily wasted litres * 30 days
    - Monthly savings = (monthly wasted litres / 1000) * tariff per 1,000 litres

    Args:
        db: SQLAlchemy session
        tariff_per_kl: Currency per 1,000 litres (> 0)
        hours_per_day: Assumed leak persistence hours per day (0 < hours <= 24)
        zone_id: Optional filter for a specific zone

    Raises:
        ValueError: If tariff_per_kl <= 0 or hours_per_day <= 0 or > 24
    """
    effective_tariff = (
        tariff_per_kl if tariff_per_kl is not None else settings.DEFAULT_WATER_TARIFF_PER_KL
    )
    if effective_tariff <= 0:
        raise ValueError(f"Water tariff must be strictly positive (> 0). Received: {effective_tariff}")

    effective_hours = (
        hours_per_day if hours_per_day is not None else settings.DEFAULT_LEAK_HOURS_PER_DAY
    )
    if effective_hours <= 0 or effective_hours > 24.0:
        raise ValueError(
            f"Assumed leak hours per day must be between 0 and 24. Received: {effective_hours}"
        )

    query = (
        db.query(Alert, Zone)
        .join(Zone, Alert.zone_id == Zone.id)
        .filter(Alert.resolved == False, Alert.alert_type == "leak")
    )
    if zone_id is not None:
        query = query.filter(Alert.zone_id == zone_id)

    alerts = query.order_by(Alert.timestamp.desc()).all()

    leak_estimates: List[LeakSavingsEstimate] = []
    total_daily_wasted = 0.0
    total_monthly_wasted = 0.0
    total_monthly_savings = 0.0
    actionable_count = 0

    flow_pattern = re.compile(r"average flow of\s+([\d.]+)\s*L/h", re.IGNORECASE)
    fallback_flow_pattern = re.compile(r"([\d.]+)\s*L/h", re.IGNORECASE)

    for alert, zone in alerts:
        # Attempt to extract credible flow rate from alert diagnostic message
        match = flow_pattern.search(alert.message) or fallback_flow_pattern.search(alert.message)

        if match:
            try:
                flow_lph = round(float(match.group(1)), 2)
            except (ValueError, TypeError):
                flow_lph = None
        else:
            flow_lph = None

        if flow_lph is not None and flow_lph > 0:
            daily_wasted = round(flow_lph * effective_hours, 2)
            monthly_wasted = round(daily_wasted * 30.0, 2)
            monthly_savings = round((monthly_wasted / 1000.0) * effective_tariff, 2)

            total_daily_wasted += daily_wasted
            total_monthly_wasted += monthly_wasted
            total_monthly_savings += monthly_savings
            actionable_count += 1

            status = "estimated"
            msg = f"Leak flow rate of {flow_lph} L/h extracted from detector telemetry."
        else:
            daily_wasted = None
            monthly_wasted = None
            monthly_savings = None
            status = "unavailable"
            msg = "Flow rate telemetry unavailable for this alert. Savings cannot be calculated without flow measurement."

        leak_estimates.append(
            LeakSavingsEstimate(
                alert_id=alert.id,
                zone_id=zone.id,
                zone_name=zone.name,
                timestamp=alert.timestamp,
                leak_flow_lph=flow_lph,
                assumed_hours_per_day=effective_hours,
                daily_wasted_litres=daily_wasted,
                monthly_wasted_litres=monthly_wasted,
                monthly_savings=monthly_savings,
                status=status,
                message=msg,
                is_estimate=True,
            )
        )

    return ConservationSavingsResponse(
        tariff_per_kl=round(effective_tariff, 2),
        currency="USD",
        assumed_hours_per_day=round(effective_hours, 1),
        total_leaks_evaluated=len(alerts),
        actionable_leaks_count=actionable_count,
        total_daily_wasted_litres=round(total_daily_wasted, 2),
        total_monthly_wasted_litres=round(total_monthly_wasted, 2),
        total_monthly_savings=round(total_monthly_savings, 2),
        leak_estimates=leak_estimates,
        disclaimer="Estimated savings are projections based on assumed daily leak duration and configured tariffs. They are not guaranteed or measured savings.",
    )
