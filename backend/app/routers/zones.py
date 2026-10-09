"""AquaWatch Zones Router.

Exposes endpoints for listing monitoring zones and retrieving individual zone details.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.zone import ZoneResponse
from app.services import zone_service

router = APIRouter(prefix="/zones", tags=["Zones"])


@router.get(
    "",
    response_model=List[ZoneResponse],
    status_code=status.HTTP_200_OK,
    summary="List all zones",
    description="Returns all monitored zones ordered by id ascending.",
)
def get_zones(db: Session = Depends(get_db)) -> List[ZoneResponse]:
    """Retrieve all monitored zones."""
    return zone_service.get_all_zones(db)


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single zone",
    description="Retrieves a specific zone by identifier. Returns 404 if not found.",
)
def get_zone(zone_id: int, db: Session = Depends(get_db)) -> ZoneResponse:
    """Retrieve an individual zone by its identifier."""
    zone = zone_service.get_zone_by_id(db, zone_id=zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with id {zone_id} not found",
        )
    return zone
