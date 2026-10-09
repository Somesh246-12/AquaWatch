"""Zone service layer handling zone queries."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.zone import Zone


def get_all_zones(db: Session) -> List[Zone]:
    """Retrieves all monitored zones ordered by id ascending."""
    return db.query(Zone).order_by(Zone.id.asc()).all()


def get_zone_by_id(db: Session, zone_id: int) -> Optional[Zone]:
    """Retrieves a single zone by identifier, or None if not found."""
    return db.query(Zone).filter(Zone.id == zone_id).first()
