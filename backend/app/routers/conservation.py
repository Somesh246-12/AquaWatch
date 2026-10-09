"""AquaWatch Conservation Intelligence Router.

Exposes endpoints for zone water budget evaluation, data-driven conservation tips,
and leak savings calculations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.conservation import (
    ConservationBudgetsResponse,
    ConservationSavingsResponse,
    ConservationTipsResponse,
)
from app.services import conservation_service, zone_service

router = APIRouter(prefix="/conservation", tags=["Conservation"])


@router.get(
    "/budgets",
    response_model=ConservationBudgetsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get water budget statuses",
    description="Calculates daily consumption, remaining allowances, and budget status (normal, warning, exceeded) per zone.",
)
def get_budgets(
    date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format (defaults to latest available)"),
    db: Session = Depends(get_db),
) -> ConservationBudgetsResponse:
    """Retrieve daily water budget performance across monitored zones."""
    try:
        return conservation_service.calculate_zone_budgets(db=db, target_date=date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/tips",
    response_model=ConservationTipsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conservation recommendations",
    description="Generates prioritized, non-duplicated conservation recommendations from database observations and alerts.",
)
def get_tips(
    date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format (defaults to latest available)"),
    db: Session = Depends(get_db),
) -> ConservationTipsResponse:
    """Retrieve prioritized conservation recommendations based on active leaks and usage trends."""
    try:
        return conservation_service.generate_conservation_recommendations(db=db, target_date=date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/savings",
    response_model=ConservationSavingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate leak savings",
    description="Estimates volumetric water loss and financial savings from repairing detected leaks.",
)
def get_savings(
    tariff_per_kl: Optional[float] = Query(None, description="Water tariff in currency per 1,000 litres (> 0)"),
    hours_per_day: Optional[float] = Query(None, description="Assumed leak persistence hours per day (0-24)"),
    zone_id: Optional[int] = Query(None, description="Optional zone filter"),
    db: Session = Depends(get_db),
) -> ConservationSavingsResponse:
    """Calculate projected volumetric and monetary savings from repairing detected leaks."""
    if tariff_per_kl is not None and tariff_per_kl <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tariff_per_kl must be strictly greater than 0.",
        )

    if hours_per_day is not None and (hours_per_day <= 0 or hours_per_day > 24.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hours_per_day must be between 0 and 24.",
        )

    if zone_id is not None:
        if zone_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="zone_id must be a positive integer.",
            )
        zone = zone_service.get_zone_by_id(db, zone_id=zone_id)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with id {zone_id} not found.",
            )

    try:
        return conservation_service.calculate_leak_savings(
            db=db,
            tariff_per_kl=tariff_per_kl,
            hours_per_day=hours_per_day,
            zone_id=zone_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
