"""Summary service layer computing dashboard KPIs and budget statuses."""

from datetime import timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.reading import Reading
from app.models.zone import Zone
from app.schemas.summary import (
    DashboardSummaryResponse,
    TopZoneSummary,
    ZoneBudgetSummary,
)


def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
    """Calculates live KPI metrics, 24h comparisons, weekly trends, and zone budget statuses.

    Calculates metrics relative to the latest timestamp present in the database
    to support historical simulated datasets and live IoT streams alike.
    """
    zones = db.query(Zone).order_by(Zone.id.asc()).all()
    active_alerts_count = (
        db.query(func.count(Alert.id)).filter(Alert.resolved == False).scalar() or 0
    )

    max_timestamp = db.query(func.max(Reading.timestamp)).scalar()
    if not max_timestamp or not zones:
        # Fallback for empty database
        zone_summaries = [
            ZoneBudgetSummary(
                id=z.id,
                name=z.name,
                type=z.type,
                daily_budget_litres=z.daily_budget_litres,
                today_usage_litres=0.0,
                budget_used_percent=0.0,
            )
            for z in zones
        ]
        return DashboardSummaryResponse(
            today_usage_litres=0.0,
            yesterday_usage_litres=0.0,
            change_percent=0.0,
            weekly_usage_litres=0.0,
            top_zone=None,
            active_alerts=active_alerts_count,
            zones=zone_summaries,
        )

    # Determine reference calendar days
    today_date = max_timestamp.date()
    yesterday_date = today_date - timedelta(days=1)
    week_start_date = today_date - timedelta(days=6)

    today_str = str(today_date)
    yesterday_str = str(yesterday_date)
    week_start_str = str(week_start_date)

    date_col = func.date(Reading.timestamp)

    # Today's total usage
    today_usage = (
        db.query(func.sum(Reading.litres))
        .filter(date_col == today_str)
        .scalar()
        or 0.0
    )

    # Yesterday's total usage
    yesterday_usage = (
        db.query(func.sum(Reading.litres))
        .filter(date_col == yesterday_str)
        .scalar()
        or 0.0
    )

    # Weekly total usage (7 days inclusive)
    weekly_usage = (
        db.query(func.sum(Reading.litres))
        .filter(date_col >= week_start_str, date_col <= today_str)
        .scalar()
        or 0.0
    )

    # Change percent calculation (safe zero-denominator handling)
    if yesterday_usage > 0.0:
        change_pct = round(((today_usage - yesterday_usage) / yesterday_usage) * 100.0, 2)
    else:
        change_pct = 0.0

    # Per-zone today usage breakdown
    zone_usage_query = (
        db.query(Reading.zone_id, func.sum(Reading.litres))
        .filter(date_col == today_str)
        .group_by(Reading.zone_id)
        .all()
    )
    today_zone_map = {row[0]: float(row[1]) for row in zone_usage_query}

    zone_summaries: List[ZoneBudgetSummary] = []
    top_zone_obj: Optional[TopZoneSummary] = None
    max_zone_usage = -1.0

    for z in zones:
        usage = today_zone_map.get(z.id, 0.0)
        pct = (
            round((usage / z.daily_budget_litres) * 100.0, 1)
            if z.daily_budget_litres > 0
            else 0.0
        )
        zone_summaries.append(
            ZoneBudgetSummary(
                id=z.id,
                name=z.name,
                type=z.type,
                daily_budget_litres=z.daily_budget_litres,
                today_usage_litres=round(usage, 2),
                budget_used_percent=pct,
            )
        )

        if usage > max_zone_usage:
            max_zone_usage = usage
            top_zone_obj = TopZoneSummary(
                id=z.id,
                name=z.name,
                litres=round(usage, 2),
            )

    return DashboardSummaryResponse(
        today_usage_litres=round(today_usage, 2),
        yesterday_usage_litres=round(yesterday_usage, 2),
        change_percent=change_pct,
        weekly_usage_litres=round(weekly_usage, 2),
        top_zone=top_zone_obj,
        active_alerts=active_alerts_count,
        zones=zone_summaries,
    )
