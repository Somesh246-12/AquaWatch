"""Reading service layer handling querying, filtering, aggregation, and creation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.reading import Reading
from app.models.zone import Zone
from app.schemas.reading import ReadingCreate


def get_reading_by_id(db: Session, reading_id: int) -> Optional[Reading]:
    """Retrieves a single reading by its identifier."""
    return db.query(Reading).filter(Reading.id == reading_id).first()


def create_reading(db: Session, reading_in: ReadingCreate) -> Reading:
    """Inserts a new water reading after verifying the referenced zone exists.

    Raises:
        ValueError: If the referenced zone does not exist.
    """
    zone_exists = db.query(Zone.id).filter(Zone.id == reading_in.zone_id).first()
    if not zone_exists:
        raise ValueError(f"Zone with id {reading_in.zone_id} does not exist.")

    db_reading = Reading(
        zone_id=reading_in.zone_id,
        timestamp=reading_in.timestamp,
        litres=reading_in.litres,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


def get_readings_hourly(
    db: Session,
    zone_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Reading]:
    """Retrieves individual hourly readings with optional zone and temporal filters."""
    query = db.query(Reading)

    if zone_id is not None:
        query = query.filter(Reading.zone_id == zone_id)
    if start is not None:
        query = query.filter(Reading.timestamp >= start)
    if end is not None:
        query = query.filter(Reading.timestamp <= end)

    return (
        query.order_by(Reading.timestamp.asc(), Reading.zone_id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_readings_daily(
    db: Session,
    zone_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Aggregates water consumption by calendar date and zone."""
    date_col = func.date(Reading.timestamp).label("calendar_date")
    total_col = func.sum(Reading.litres).label("daily_litres")

    query = (
        db.query(
            date_col,
            Reading.zone_id,
            Zone.name.label("zone_name"),
            total_col,
        )
        .join(Zone, Reading.zone_id == Zone.id)
    )

    if zone_id is not None:
        query = query.filter(Reading.zone_id == zone_id)
    if start is not None:
        query = query.filter(Reading.timestamp >= start)
    if end is not None:
        query = query.filter(Reading.timestamp <= end)

    query = query.group_by(date_col, Reading.zone_id, Zone.name)
    query = query.order_by(date_col.asc(), Reading.zone_id.asc())

    rows = query.offset(offset).limit(limit).all()

    return [
        {
            "date": str(r[0]),
            "zone_id": r[1],
            "zone_name": r[2],
            "litres": round(float(r[3]), 2) if r[3] is not None else 0.0,
        }
        for r in rows
    ]
