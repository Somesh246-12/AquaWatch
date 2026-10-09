"""AquaWatch Readings Router.

Exposes endpoints for querying consumption time-series, retrieving daily/hourly
aggregations, fetching individual readings, and ingesting live sensor readings.
"""

from datetime import datetime
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reading import DailyReadingResponse, ReadingCreate, ReadingResponse
from app.services import reading_service, zone_service

router = APIRouter(prefix="/readings", tags=["Readings"])


@router.get(
    "",
    response_model=Union[List[ReadingResponse], List[DailyReadingResponse]],
    status_code=status.HTTP_200_OK,
    summary="Query readings",
    description="Retrieve water consumption readings filtered by zone, date range, and aggregation.",
)
def get_readings(
    zone_id: Optional[int] = Query(None, description="Optional zone ID filter"),
    start: Optional[datetime] = Query(None, description="Start timestamp (ISO-8601)"),
    end: Optional[datetime] = Query(None, description="End timestamp (ISO-8601)"),
    aggregation: str = Query("hourly", description="Aggregation level: 'hourly' or 'daily'"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
) -> Union[List[ReadingResponse], List[DailyReadingResponse]]:
    """Query time-series water consumption readings with filtering and aggregation."""
    # Validate aggregation parameter
    agg_normalized = aggregation.lower().strip()
    if agg_normalized not in ("hourly", "daily"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid aggregation '{aggregation}'. Supported values are 'hourly' or 'daily'.",
        )

    # Validate temporal range
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start timestamp must be earlier than or equal to end timestamp.",
        )

    # Validate zone existence if zone_id provided
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

    if agg_normalized == "daily":
        return reading_service.get_readings_daily(
            db=db,
            zone_id=zone_id,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        )

    return reading_service.get_readings_hourly(
        db=db,
        zone_id=zone_id,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{reading_id}",
    response_model=ReadingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reading by ID",
    description="Retrieve a single consumption reading by identifier. Returns 404 if not found.",
)
def get_reading(reading_id: int, db: Session = Depends(get_db)) -> ReadingResponse:
    """Retrieve an individual reading record."""
    reading = reading_service.get_reading_by_id(db, reading_id=reading_id)
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reading with id {reading_id} not found.",
        )
    return reading


@router.post(
    "",
    response_model=ReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest new reading",
    description="Ingest a live water consumption reading from an IoT sensor or simulation.",
)
def create_reading(
    reading_in: ReadingCreate,
    db: Session = Depends(get_db),
) -> ReadingResponse:
    """Ingest a new live reading into the system."""
    try:
        return reading_service.create_reading(db, reading_in=reading_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
